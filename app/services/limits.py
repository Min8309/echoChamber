"""Persistent, atomic limits shared by every LLM entry point and worker.

One daily unit is one attempted SDK operation, not a token or currency amount.
Never trust arbitrary X-Forwarded-For headers here: the ASGI server must first
validate its trusted proxy chain before populating request.client.
"""

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "echochamber.sqlite3"


def enabled(name):
    return os.getenv(
        name, "true" if name in {"DEMO_READ_ONLY", "DISABLE_DOCS"} else "false"
    ).strip().lower() in {"1", "true", "yes", "on"}


def setting(name, default):
    try:
        value = int(os.getenv(name, str(default)))
        if value < 0:
            raise ValueError
        return value
    except ValueError as error:
        raise HTTPException(503, f"서버의 {name} 설정을 확인해 주세요.") from error


def connect():
    path = Path(
        os.getenv("ECHOCHAMBER_LIMITS_DB_PATH")
        or os.getenv("ECHOCHAMBER_DB_PATH")
        or DEFAULT_DB
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.execute(
        "CREATE TABLE IF NOT EXISTS llm_requests (ip TEXT NOT NULL, ts REAL NOT NULL)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS llm_requests_ip_ts ON llm_requests(ip, ts)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS llm_daily (day TEXT PRIMARY KEY, units INTEGER NOT NULL)"
    )
    return db


def reject(message, retry):
    raise HTTPException(429, message, headers={"Retry-After": str(max(1, int(retry)))})


def day_and_retry(now):
    day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    return day, 86400 - int(now % 86400)


def consume_request(ip, minimum_units=1, now=None):
    now = time.time() if now is None else now
    day, retry = day_and_retry(now)
    hourly = setting("LLM_REQUESTS_PER_HOUR", 10)
    cap = setting("LLM_DAILY_UNIT_CAP", 100)
    digest = hashlib.sha256(ip.encode()).hexdigest()
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM llm_requests WHERE ts <= ?", (now - 3600,))
        count, oldest = db.execute(
            "SELECT count(*), min(ts) FROM llm_requests WHERE ip = ?", (digest,)
        ).fetchone()
        if count >= hourly:
            reject(
                "시간당 AI 요청 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.",
                (oldest or now) + 3600 - now + 1,
            )
        row = db.execute("SELECT units FROM llm_daily WHERE day = ?", (day,)).fetchone()
        if (row[0] if row else 0) + minimum_units > cap:
            reject(
                "서버의 오늘 AI 호출 한도가 부족합니다. 단계 수를 줄이거나 다음 날 다시 시도해 주세요.",
                retry,
            )
        db.execute("INSERT INTO llm_requests VALUES (?, ?)", (digest, now))
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def charge_llm_unit():
    """Check immediately before every outbound SDK call; failed attempts count."""
    now = time.time()
    day, retry = day_and_retry(now)
    cap = setting("LLM_DAILY_UNIT_CAP", 100)
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT units FROM llm_daily WHERE day = ?", (day,)).fetchone()
        if (row[0] if row else 0) >= cap:
            reject("서버의 오늘 AI 호출 한도에 도달했습니다.", retry)
        db.execute(
            "INSERT INTO llm_daily VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET units = units + 1",
            (day,),
        )
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


async def guard_llm_request(request: Request):
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    path = request.url.path
    workbench = path in {"/api/runs", "/api/runs/stream"}
    if workbench and body.get("engine", "rules") == "rules":
        return  # Free local rules execution never consumes an LLM budget.
    default_steps = 6 if workbench else (3 if path.endswith("run") else 1)
    steps = body.get("steps", default_steps)
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 20:
        steps = 1  # The endpoint's Pydantic model rejects invalid input.
    if workbench or path.startswith("/simulation/"):
        minimum = steps * (3 if "autonomous" in path else 2)
    elif path == "/analysis/messages":
        from app.routers.ingestion import messages
        minimum = max(1, len(messages))
    elif path == "/conversations":
        minimum = 2
    else:
        minimum = 1
    await run_in_threadpool(
        consume_request, request.client.host if request.client else "unknown", minimum
    )


def require_writable():
    if enabled("DEMO_READ_ONLY"):
        raise HTTPException(
            403, "데모 읽기 전용 모드에서는 에이전트·기억·메시지를 추가할 수 없습니다."
        )
