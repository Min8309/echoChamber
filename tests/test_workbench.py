"""Run with .venv/bin/python -m unittest discover -s tests -v."""

import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

import requests

ROOT = Path(__file__).resolve().parents[1]


class WorkbenchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = str(Path(cls.temp.name) / "runs.sqlite3")
        env = {**os.environ, "ECHOCHAMBER_DB_PATH": cls.db}
        env.pop("OPENAI_API_KEY", None)
        env.pop("ECHOCHAMBER_API_KEY", None)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.log = tempfile.TemporaryFile()
        cls.process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            cwd=ROOT,
            env=env,
            stdout=cls.log,
            stderr=cls.log,
        )
        for _ in range(100):
            try:
                if requests.get(cls.base + "/health", timeout=0.5).ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.1)
        cls.process.terminate()
        cls.log.seek(0)
        raise RuntimeError(cls.log.read().decode())

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.log.close()
        cls.temp.cleanup()

    def test_startup_without_api_key_and_react_bundle(self):
        response = requests.get(self.base + "/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="root"', response.text)
        self.assertEqual(
            requests.get(self.base + "/api/capabilities").json()["engines"], ["rules"]
        )
        agents = requests.get(self.base + "/api/agents").json()
        self.assertEqual(len(agents), 3)
        self.assertEqual(len({a["name"] for a in agents}), 3)
        self.assertEqual(requests.get(self.base + "/agents").status_code, 200)

    def test_run_chain_network_and_durable_snapshot(self):
        response = requests.post(
            self.base + "/api/runs",
            json={"topic": "카페에서 주말 파티가 열린다", "steps": 6, "seed": 7},
        )
        self.assertEqual(response.status_code, 201)
        run = response.json()
        self.assertEqual(run["completed_steps"], 6)
        self.assertEqual(len(run["agents"]), 3)
        self.assertEqual(sum(e["count"] for e in run["network"]["edges"]), 6)
        self.assertEqual(run["events"][0]["input_text"], run["topic"])
        for previous, current in zip(run["events"], run["events"][1:]):
            self.assertEqual(current["speaker_id"], previous["listener_id"])
            self.assertEqual(current["input_text"], previous["utterance"])
            self.assertLess(current["confidence"], previous["confidence"])
        for event in run["events"]:
            self.assertNotEqual(event["speaker_id"], event["listener_id"])
        self.assertEqual(
            requests.get(self.base + "/api/runs/" + run["run_id"]).json(), run
        )
        self.assertEqual(
            requests.get(self.base + "/api/runs/" + run["run_id"] + "/network").json(),
            run["network"],
        )
        with sqlite3.connect(self.db) as db:
            saved = json.loads(
                db.execute(
                    "SELECT payload FROM runs WHERE id = ?", (run["run_id"],)
                ).fetchone()[0]
            )
        self.assertEqual(saved, run)
        self.assertIn(
            run["run_id"],
            [r["run_id"] for r in requests.get(self.base + "/api/runs").json()],
        )

    def test_live_stream_orders_steps_then_commits(self):
        response = requests.post(
            self.base + "/api/runs/stream",
            json={"topic": "도서관 행사 소식", "steps": 3},
            stream=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        frames = []
        kind = None
        for raw in response.iter_lines():
            line = raw.decode("utf-8")
            if line.startswith("event: "):
                kind = line[7:]
            if line.startswith("data: "):
                frames.append((kind, json.loads(line[6:])))
        self.assertEqual(
            [f[0] for f in frames],
            [
                "start",
                "step",
                "analysis",
                "step",
                "analysis",
                "step",
                "analysis",
                "complete",
            ],
        )
        self.assertEqual(
            [f[1]["event"]["step"] for f in frames if f[0] == "step"], [1, 2, 3]
        )
        run = frames[-1][1]
        self.assertEqual(
            requests.get(self.base + "/api/runs/" + run["run_id"]).json(), run
        )

    def test_invalid_input_and_missing_key_do_not_create_runs(self):
        before = requests.get(self.base + "/api/runs").json()
        for payload in [
            {"topic": "   "},
            {"topic": "주제", "steps": 0},
            {"topic": "주제", "steps": 21},
            {"topic": "주제", "engine": "unknown"},
        ]:
            self.assertEqual(
                requests.post(self.base + "/api/runs", json=payload).status_code, 422
            )
        for path in ["/api/runs", "/api/runs/stream"]:
            self.assertEqual(
                requests.post(
                    self.base + path, json={"topic": "주제", "engine": "openai"}
                ).status_code,
                409,
            )
        self.assertEqual(
            requests.get(self.base + "/api/runs/no-such-run").status_code, 404
        )
        self.assertEqual(requests.get(self.base + "/api/runs").json(), before)

    def test_z_history_survives_server_restart(self):
        run = requests.post(
            self.base + "/api/runs", json={"topic": "재시작 보존 실험", "steps": 2}
        ).json()
        cls = type(self)
        cls.process.terminate()
        cls.process.wait(timeout=10)
        env = {**os.environ, "ECHOCHAMBER_DB_PATH": cls.db}
        env.pop("OPENAI_API_KEY", None)
        env.pop("ECHOCHAMBER_API_KEY", None)
        cls.process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            cwd=ROOT,
            env=env,
            stdout=cls.log,
            stderr=cls.log,
        )
        for attempt in range(100):
            try:
                if requests.get(self.base + "/health", timeout=0.5).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.1)
        self.assertEqual(
            requests.get(self.base + "/api/runs/" + run["run_id"]).json(), run
        )


class RunTransactionTests(unittest.TestCase):
    def test_failed_ai_turn_does_not_persist_partial_run(self):
        from app.routers.workbench import RunRequest, generate_run
        from app.services import runs
        from fastapi import HTTPException

        roster = [
            a.model_dump()
            for a in __import__(
                "app.services.storage", fromlist=["load_agents"]
            ).load_agents()
        ][:2]
        client = Mock()
        from app.models.analysis import DialogueAnalysis

        client.responses.parse.return_value.output_parsed = DialogueAnalysis(
            is_gossip=True,
            subject="마을",
            claim="행사 소식",
            sentiment="neutral",
            certainty="hearsay",
            confidence=0.6,
            reputation_impact=0,
            reason="테스트용 모의 분석",
        )
        client.responses.create.side_effect = [
            Mock(output_text="첫 발화"),
            RuntimeError("upstream failed"),
        ]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {"ECHOCHAMBER_DB_PATH": str(Path(directory) / "runs.sqlite3")},
            ),
        ):
            stream = generate_run(
                RunRequest(topic="주제", steps=2, engine="openai"), roster, client
            )
            self.assertEqual(next(stream)[0], "start")
            self.assertEqual(next(stream)[0], "step")
            self.assertEqual(next(stream)[0], "analysis")
            self.assertEqual(runs.list_runs(), [])
            with self.assertRaises(HTTPException) as error:
                next(stream)
            self.assertEqual(error.exception.status_code, 502)
            self.assertEqual(runs.list_runs(), [])

    def test_successful_ai_turns_use_previous_received_text(self):
        from app.routers.workbench import RunRequest, generate_run
        from app.services import runs
        from app.services.storage import load_agents

        roster = [a.model_dump() for a in load_agents()][:2]
        client = Mock()
        from app.models.analysis import DialogueAnalysis

        client.responses.parse.return_value.output_parsed = DialogueAnalysis(
            is_gossip=True,
            subject="마을",
            claim="행사 소식",
            sentiment="neutral",
            certainty="hearsay",
            confidence=0.6,
            reputation_impact=0,
            reason="테스트용 모의 분석",
        )
        client.responses.create.side_effect = [
            Mock(output_text="도서관에서 행사가 열린대요"),
            Mock(output_text="행사 소식 들으셨어요?"),
        ]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {"ECHOCHAMBER_DB_PATH": str(Path(directory) / "runs.sqlite3")},
            ),
        ):
            frames = list(
                generate_run(
                    RunRequest(topic="도서관 행사", steps=2, engine="openai"),
                    roster,
                    client,
                )
            )
            result = frames[-1][1]
            self.assertEqual(
                result["events"][1]["input_text"], "도서관에서 행사가 열린대요"
            )
            self.assertIn(
                "도서관에서 행사가 열린대요",
                client.responses.create.call_args_list[1].kwargs["input"],
            )
            self.assertEqual(runs.get_run(result["run_id"]), result)


if __name__ == "__main__":
    unittest.main()
