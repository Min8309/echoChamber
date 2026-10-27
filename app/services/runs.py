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


def save_run(run):
    db = connect()
    try:
        with db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?)",
                (run["run_id"], run["created_at"], json.dumps(run, ensure_ascii=False)),
            )
    finally:
        db.close()


def get_run(run_id):
    db = connect()
    try:
        row = db.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        db.close()


def list_runs():
    db = connect()
    try:
        rows = db.execute(
            "SELECT payload FROM runs ORDER BY created_at DESC, id DESC LIMIT 100"
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
