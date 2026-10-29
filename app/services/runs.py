"""Atomic, durable run snapshots. Legacy JSON data is read, never rewritten."""

import json
import os
import sqlite3
from pathlib import Path

from app.services.storage import load_agents


def connect():
    default = Path(__file__).resolve().parents[2] / "data" / "echochamber.sqlite3"
    path = Path(os.getenv("ECHOCHAMBER_DB_PATH", str(default)))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute(
        "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS run_access (run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE, owner TEXT NOT NULL)"
    )
    # Seed only once, including when all agents are intentionally removed later.
    db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY)")
    with db:
        if (
            db.execute("SELECT 1 FROM metadata WHERE key = 'agents_seeded'").fetchone()
            is None
        ):
            selected = []
            for agent in load_agents():
                if agent.name not in {item.name for item in selected}:
                    selected.append(agent)
            for agent in selected[:3]:
                db.execute(
                    "INSERT OR IGNORE INTO agents VALUES (?, ?)",
                    (agent.agent_id, agent.model_dump_json()),
                )
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('agents_seeded')")
    return db


def list_agents():
    db = connect()
    try:
        return [
            json.loads(row[0])
            for row in db.execute("SELECT payload FROM agents ORDER BY rowid")
        ]
    finally:
        db.close()


def save_run(run, owner=None):
    db = connect()
    try:
        with db:
            if run.get("source_data"):
                from fastapi import HTTPException

                db.execute("BEGIN IMMEDIATE")
                source = run["source_data"]
                if not db.execute(
                    "SELECT 1 FROM datasets WHERE id = ? AND owner = ?",
                    (source["dataset_id"], owner),
                ).fetchone():
                    raise HTTPException(
                        404, "연결된 실제 데이터가 삭제돼 실험을 저장하지 않았습니다."
                    )
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?)",
                (run["run_id"], run["created_at"], json.dumps(run, ensure_ascii=False)),
            )
            if owner:
                db.execute(
                    "INSERT INTO run_access VALUES (?, ?)", (run["run_id"], owner)
                )
    finally:
        db.close()


def get_run(run_id, owner=None):
    db = connect()
    try:
        row = db.execute(
            "SELECT runs.payload FROM runs LEFT JOIN run_access ON runs.id = run_access.run_id WHERE runs.id = ? AND ((? IS NULL AND run_access.owner IS NULL) OR run_access.owner = ?)",
            (run_id, owner, owner),
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        db.close()


def list_runs(owner=None):
    db = connect()
    try:
        rows = db.execute(
            "SELECT runs.payload FROM runs LEFT JOIN run_access ON runs.id = run_access.run_id WHERE (? IS NULL AND run_access.owner IS NULL) OR run_access.owner = ? ORDER BY runs.created_at DESC, runs.id DESC LIMIT 100",
            (owner, owner),
        )
        return [
            {
                key: run[key]
                for key in (
                    "run_id",
                    "created_at",
                    "topic",
                    "engine",
                    "completed_steps",
                )
            }
            for run in (json.loads(row[0]) for row in rows)
        ]
    finally:
        db.close()
