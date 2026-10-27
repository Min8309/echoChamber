"""Private, redacted research datasets with per-row resumable AI checkpoints."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from app.services import runs


PATTERNS = [
    (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[이메일]"),
    (r"(?<!\d)(?:\+82[- .]?)?0?1[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)", "[전화번호]"),
    (r"(?<!\d)0[2-6][1-5]?[- .]\d{3,4}[- .]\d{4}(?!\d)", "[전화번호]"),
    (r"https?://[^\s<>]+|www\.[^\s<>]+", "[링크]"),
    (r"(?<!\w)@[A-Za-z0-9_.-]+", "[계정]"),
]


def redact(text):
    for pattern, replacement in PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text.strip()


def connect():
    db = runs.connect()
    db.execute(
        "CREATE TABLE IF NOT EXISTS datasets (id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS datasets_owner_created ON datasets(owner, created_at)"
    )
    return db


def owner_hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def load(dataset_id, owner):
    db = connect()
    try:
        row = db.execute(
            "SELECT payload FROM datasets WHERE id = ? AND owner = ?",
            (dataset_id, owner),
        ).fetchone()
        if not row:
            raise HTTPException(
                404, "이 브라우저에서 접근할 수 있는 데이터가 없습니다."
            )
        return json.loads(row[0])
    finally:
        db.close()


def public(dataset):
    # Leases and ownership credentials are never returned to the browser.
    return {
        **dataset,
        "rows": [
            {
                key: value
                for key, value in row.items()
                if key not in {"lease", "lease_until"}
            }
            for row in dataset["rows"]
        ],
    }


def listing(owner):
    db = connect()
    try:
        items = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT payload FROM datasets WHERE owner = ? ORDER BY created_at DESC LIMIT 100",
                (owner,),
            )
        ]
        return [
            {
                "dataset_id": d["dataset_id"],
                "title": d["title"],
                "source": d["source"],
                "created_at": d["created_at"],
                "count": len(d["rows"]),
                "analysed": sum(row.get("analysis") is not None for row in d["rows"]),
            }
            for d in items
        ]
    finally:
        db.close()


def create(request, owner):
    ids = {row.local_id: str(uuid4()) for row in request.rows}
    authors, threads = {}, {}
    rows = []
    for index, row in enumerate(request.rows):
        if row.author:
            authors.setdefault(row.author, f"작성자 {len(authors) + 1}")
        if row.thread:
            threads.setdefault(row.thread, f"묶음 {len(threads) + 1}")
        rows.append(
            {
                "row_id": ids[row.local_id],
                "number": index + 1,
                "text": redact(row.text),
                "author": authors.get(row.author, "익명"),
                "thread": threads.get(row.thread),
                "reply_to_id": ids.get(row.reply_to_id),
                "rating": row.rating,
                "date": row.date.isoformat() if row.date else None,
                "status": "pending",
                "analysis": None,
                "error": None,
            }
        )
    dataset = {
        "dataset_id": str(uuid4()),
        "title": redact(request.title),
        "source": request.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }
    db = connect()
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            if (
                db.execute(
                    "SELECT count(*) FROM datasets WHERE owner = ?", (owner,)
                ).fetchone()[0]
                >= 100
            ):
                raise HTTPException(
                    429,
                    "이 브라우저의 저장 한도 100개에 도달했습니다. 불필요한 데이터를 삭제해 주세요.",
                )
            db.execute(
                "INSERT INTO datasets VALUES (?, ?, ?, ?)",
                (
                    dataset["dataset_id"],
                    owner,
                    dataset["created_at"],
                    json.dumps(dataset, ensure_ascii=False),
                ),
            )
    finally:
        db.close()
    return dataset


def claim(dataset_id, owner, attempted):
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        record = db.execute(
            "SELECT payload FROM datasets WHERE id = ? AND owner = ?",
            (dataset_id, owner),
        ).fetchone()
        if not record:
            raise HTTPException(404, "데이터가 삭제됐거나 접근할 수 없습니다.")
        data = json.loads(record[0])
        for row in data["rows"]:
            if row["row_id"] in attempted or row.get("analysis") is not None:
                continue
            if (
                row["status"] == "processing"
                and row.get("lease_until", 0) > time.time()
            ):
                continue
            row.update(
                status="processing",
                lease=str(uuid4()),
                lease_until=time.time() + 120,
                error=None,
            )
            db.execute(
                "UPDATE datasets SET payload = ? WHERE id = ? AND owner = ?",
                (json.dumps(data, ensure_ascii=False), dataset_id, owner),
            )
            db.commit()
            return row
        db.commit()
        return None
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def finish(
    dataset_id, owner, claimed, analysis=None, error=None, model=None, version=None
):
    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        record = db.execute(
            "SELECT payload FROM datasets WHERE id = ? AND owner = ?",
            (dataset_id, owner),
        ).fetchone()
        if not record:
            raise HTTPException(404, "데이터가 삭제됐습니다.")
        data = json.loads(record[0])
        for row in data["rows"]:
            if (
                row["row_id"] == claimed["row_id"]
                and row.get("lease") == claimed["lease"]
            ):
                row.update(
                    status="complete" if analysis is not None else "failed",
                    analysis=analysis,
                    error=error,
                    analysis_model=model,
                    analysis_version=version,
                )
                row.pop("lease", None)
                row.pop("lease_until", None)
                db.execute(
                    "UPDATE datasets SET payload = ? WHERE id = ? AND owner = ?",
                    (json.dumps(data, ensure_ascii=False), dataset_id, owner),
                )
                db.commit()
                return row
        db.commit()
        return None
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def delete(dataset_id, owner):
    db = connect()
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            linked = db.execute(
                "SELECT runs.id, runs.payload FROM runs JOIN run_access ON runs.id = run_access.run_id WHERE run_access.owner = ?",
                (owner,),
            ).fetchall()
            for run_id, payload in linked:
                if (json.loads(payload).get("source_data") or {}).get(
                    "dataset_id"
                ) == dataset_id:
                    db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            result = db.execute(
                "DELETE FROM datasets WHERE id = ? AND owner = ?", (dataset_id, owner)
            )
            if not result.rowcount:
                raise HTTPException(404, "데이터가 없거나 접근할 수 없습니다.")
    finally:
        db.close()


def basic_stats(texts):
    n = len(texts)
    return {
        "count": n,
        "average_length": round(sum(map(len, texts)) / n, 1) if n else None,
        "question_pct": round(
            sum(bool(re.search(r"[?？]|까요|나요", t)) for t in texts) * 100 / n, 1
        )
        if n
        else None,
        "uncertain_expression_pct": round(
            sum(
                bool(re.search(r"카더라|들었|라더|것 같|아마|모르|추측|소문", t))
                for t in texts
            )
            * 100
            / n,
            1,
        )
        if n
        else None,
    }


def ai_stats(analyses, total):
    items = [a for a in analyses if a is not None]
    n = len(items)
    return {
        "analysed": n,
        "total": total,
        "gossip_pct": round(sum(a["is_gossip"] for a in items) * 100 / n, 1)
        if n
        else None,
        "speculation_pct": round(
            sum(a["certainty"] == "speculation" for a in items) * 100 / n, 1
        )
        if n
        else None,
        "negative_pct": round(
            sum(a["sentiment"] == "negative" for a in items) * 100 / n, 1
        )
        if n
        else None,
        "average_reputation_impact": round(
            sum(a["reputation_impact"] for a in items) / n, 3
        )
        if n
        else None,
    }
