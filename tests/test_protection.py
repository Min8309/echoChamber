"""Limits are exercised through real FastAPI/Uvicorn HTTP, using a fake SDK."""

import concurrent.futures
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
VALID_ANALYSIS = {"text": "도서관 행사 소식", "speaker_name": "A", "listener_name": "B"}
RUN_KEY = {"X-Dataset-Key": "c" * 64}


class LiveServer:
    def __init__(self, **settings):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "test.sqlite3")
        self.env = {
            **os.environ,
            "ECHOCHAMBER_DB_PATH": self.db,
            "ECHOCHAMBER_LIMITS_DB_PATH": self.db,
            "ECHOCHAMBER_API_KEY": "test-only-sdk-is-mocked",
            "FORWARDED_ALLOW_IPS": "",
            "LLM_DAILY_UNIT_CAP": "100",
            "LLM_REQUESTS_PER_HOUR": "100",
            "DEMO_READ_ONLY": "false",
            "DISABLE_DOCS": "false",
            **settings,
        }
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.log = tempfile.TemporaryFile()
        self.start()

    def start(self):
        script = f"import sys; sys.path.insert(0, 'tests'); from fake_provider import FakeOpenAI; import app.services.ai_client as ai; ai.OpenAI = FakeOpenAI; import os; import app.services.collection as collector; from fake_provider import FakeOfficialHTTP; collector.OfficialHTTP = FakeOfficialHTTP if os.getenv('FAKE_COLLECTION') == 'true' else collector.OfficialHTTP; import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port={self.port})"
        self.process = subprocess.Popen(
            [str(ROOT / ".venv/bin/python"), "-c", script],
            cwd=ROOT,
            env=self.env,
            stdout=self.log,
            stderr=self.log,
        )
        for _ in range(100):
            try:
                if self.get("/health").ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.05)
        raise RuntimeError("Test server did not start")

    def get(self, path):
        headers = RUN_KEY if path.startswith("/api/runs") else None
        return requests.get(self.base + path, headers=headers, timeout=10)

    def post(self, path, body=None, **kwargs):
        if path.startswith("/api/runs"):
            kwargs.setdefault("headers", RUN_KEY)
        return requests.post(self.base + path, json=body or {}, timeout=10, **kwargs)

    def units(self):
        with sqlite3.connect(self.db) as db:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='llm_daily'"
            ).fetchone():
                return 0
            return db.execute(
                "SELECT coalesce(sum(units), 0) FROM llm_daily"
            ).fetchone()[0]

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=10)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
        self.log.seek(0)
        log = self.log.read().decode()
        self.log.close()
        self.directory.cleanup()
        if "ERROR:    Exception in ASGI application" in log:
            raise AssertionError(log[-4000:])


def frames(response):
    kind = None
    for raw in response.iter_lines(chunk_size=1):
        line = raw.decode("utf-8")
        if line.startswith("event: "):
            kind = line[7:]
        if line.startswith("data: "):
            yield kind, json.loads(line[6:])


class ProtectionHTTPTests(unittest.TestCase):
    def test_all_llm_routes_share_hourly_limit_even_with_spoofed_header(self):
        with LiveServer(LLM_REQUESTS_PER_HOUR="1") as server:
            self.assertEqual(
                server.post(
                    "/api/runs", {"topic": "행사", "steps": 1, "engine": "openai"}
                ).status_code,
                201,
            )
            cases = {
                "/simulation/step": {"topic": "행사"},
                "/simulation/run": {"topic": "행사", "steps": 1},
                "/simulation/autonomous-step": {},
                "/simulation/autonomous-run": {"steps": 1},
                "/conversations": {
                    "speaker_id": "a",
                    "listener_id": "b",
                    "topic": "행사",
                },
                "/agents/missing/reflect": {},
                "/planning/missing": {},
                "/analysis/dialogue": VALID_ANALYSIS,
                "/analysis/messages": {},
                "/api/runs": {"topic": "행사", "steps": 1, "engine": "openai"},
                "/api/runs/stream": {"topic": "행사", "steps": 1, "engine": "openai"},
            }
            for path, body in cases.items():
                with self.subTest(path=path):
                    response = server.post(
                        path, body, headers={"X-Forwarded-For": "203.0.113.22"}
                    )
                    self.assertEqual(response.status_code, 429, response.text)
                    self.assertGreater(int(response.headers["Retry-After"]), 0)
            self.assertEqual(server.units(), 2)
            server.stop()
            server.start()
            self.assertEqual(
                server.post("/analysis/dialogue", VALID_ANALYSIS).status_code, 429
            )

    def test_daily_preflight_steps_actual_calls_and_rules_exemption(self):
        with LiveServer(LLM_DAILY_UNIT_CAP="3") as server:
            rejected = server.post(
                "/api/runs", {"topic": "행사", "steps": 2, "engine": "openai"}
            )
            self.assertEqual(rejected.status_code, 429)
            self.assertEqual(server.units(), 0)
            self.assertEqual(
                server.post(
                    "/api/runs", {"topic": "행사", "steps": 1, "engine": "openai"}
                ).status_code,
                201,
            )
            self.assertEqual(server.units(), 2)
            self.assertEqual(
                server.post("/analysis/dialogue", VALID_ANALYSIS).status_code, 200
            )
            self.assertEqual(server.units(), 3)
            self.assertEqual(
                server.post("/analysis/dialogue", VALID_ANALYSIS).status_code, 429
            )
            self.assertEqual(
                server.post(
                    "/api/runs", {"steps": 2, "mode": "autonomous", "engine": "rules"}
                ).status_code,
                201,
            )
            self.assertEqual(server.units(), 3)

    def test_atomic_cap_under_parallel_real_http_requests(self):
        with LiveServer(LLM_DAILY_UNIT_CAP="3") as server:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                statuses = list(
                    pool.map(
                        lambda _: (
                            server.post(
                                "/analysis/dialogue", VALID_ANALYSIS
                            ).status_code
                        ),
                        range(8),
                    )
                )
            self.assertEqual(statuses.count(200), 3, statuses)
            self.assertEqual(statuses.count(429), 5, statuses)
            self.assertEqual(server.units(), 3)

    def test_read_only_docs_and_cors(self):
        with LiveServer(
            DEMO_READ_ONLY="true",
            DISABLE_DOCS="true",
            CORS_ORIGINS="https://lab.example.org",
        ) as server:
            for path in ["/agents", "/agents/missing/memories", "/ingest/messages"]:
                self.assertEqual(server.post(path).status_code, 403)
            for path in ["/docs", "/redoc", "/openapi.json"]:
                self.assertEqual(server.get(path).status_code, 404)
            self.assertEqual(server.get("/api/agents").status_code, 200)
            self.assertEqual(
                server.post("/api/runs", {"topic": "행사", "steps": 1}).status_code, 201
            )
            for origin, expected in [
                ("https://lab.example.org", 200),
                ("https://evil.example", 400),
            ]:
                response = requests.options(
                    server.base + "/api/runs",
                    headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
                    timeout=10,
                )
                self.assertEqual(response.status_code, expected)
                if expected == 200:
                    self.assertEqual(
                        response.headers.get("Access-Control-Allow-Origin"), origin
                    )

    def test_stream_delivers_analysis_after_message_and_saves(self):
        with LiveServer() as server:
            response = server.post(
                "/api/runs/stream",
                {"steps": 2, "mode": "autonomous", "engine": "openai"},
                stream=True,
            )
            events = list(frames(response))
            self.assertEqual(
                [kind for kind, _ in events],
                ["start", "step", "analysis", "step", "analysis", "complete"],
            )
            self.assertNotIn("analysis", events[1][1]["event"])
            self.assertTrue(events[2][1]["analysis"]["is_gossip"])
            saved = events[-1][1]
            self.assertEqual(saved["mode"], "autonomous")
            self.assertTrue(all(e["analysis"] for e in saved["events"]))
            self.assertEqual(server.get("/api/runs/" + saved["run_id"]).json(), saved)
            self.assertEqual(server.units(), 4)

    def test_daily_cap_error_is_streamed_as_429_during_concurrent_use(self):
        with LiveServer(LLM_DAILY_UNIT_CAP="4", FAKE_PARSE_DELAY="1") as server:
            response = server.post(
                "/api/runs/stream",
                {"topic": "동시 예산 실험", "steps": 2, "engine": "openai"},
                stream=True,
            )
            iterator = frames(response)
            seen = []
            for kind, data in iterator:
                seen.append((kind, data))
                if kind == "step":
                    break
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                statuses = list(
                    pool.map(
                        lambda _: (
                            server.post(
                                "/analysis/dialogue", VALID_ANALYSIS
                            ).status_code
                        ),
                        range(3),
                    )
                )
            seen.extend(iterator)
            self.assertTrue(all(code in {200, 429} for code in statuses))
            self.assertEqual(seen[-1][0], "error")
            self.assertEqual(seen[-1][1]["status"], 429)
            self.assertGreater(int(seen[-1][1]["retry_after"]), 0)
            self.assertEqual(server.units(), 4)
            self.assertEqual(server.get("/api/runs").json(), [])

    def test_failed_analysis_stream_does_not_save_partial_run(self):
        with LiveServer(FAKE_PARSE_FAIL="true") as server:
            response = server.post(
                "/api/runs/stream",
                {"topic": "행사", "steps": 1, "engine": "openai"},
                stream=True,
            )
            events = list(frames(response))
            self.assertEqual([kind for kind, _ in events], ["start", "step", "error"])
            self.assertEqual(events[-1][1]["status"], 502)
            self.assertEqual(server.get("/api/runs").json(), [])
            self.assertEqual(server.units(), 2)

    def test_disconnect_stops_remaining_calls_and_does_not_save(self):
        with LiveServer(FAKE_CREATE_DELAY=".05", FAKE_PARSE_DELAY=".5") as server:
            response = server.post(
                "/api/runs/stream",
                {"topic": "중단 실험", "steps": 3, "engine": "openai"},
                stream=True,
            )
            for kind, data in frames(response):
                if kind == "step":
                    break
            response.close()
            time.sleep(0.8)
            self.assertLessEqual(server.units(), 2)
            self.assertEqual(server.get("/api/runs").json(), [])


class LimitClockTests(unittest.TestCase):
    def test_sliding_window_and_utc_day_reset(self):
        from app.services import limits

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                os.environ,
                {
                    "ECHOCHAMBER_LIMITS_DB_PATH": str(
                        Path(directory) / "limits.sqlite3"
                    ),
                    "LLM_REQUESTS_PER_HOUR": "1",
                    "LLM_DAILY_UNIT_CAP": "1",
                },
            ),
        ):
            limits.consume_request("ip", now=100)
            with self.assertRaises(Exception) as error:
                limits.consume_request("ip", now=3699)
            self.assertEqual(error.exception.status_code, 429)
            limits.consume_request("ip", now=3701)
            with patch("app.services.limits.time.time", return_value=80000):
                limits.charge_llm_unit()
                with self.assertRaises(Exception) as error:
                    limits.charge_llm_unit()
                self.assertEqual(error.exception.status_code, 429)
            with patch("app.services.limits.time.time", return_value=86401):
                limits.charge_llm_unit()
