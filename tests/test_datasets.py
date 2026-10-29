import csv
import io
import json
import sqlite3
import time
import unittest
import requests

from test_protection import LiveServer, frames

KEY = {"X-Dataset-Key": "a" * 64}
OTHER = {"X-Dataset-Key": "b" * 64}


def payload():
    return {
        "title": "리뷰 <연구>",
        "source": "review",
        "reviewed": True,
        "rows": [
            {
                "local_id": "original-id-one",
                "text": "아마 좋을 것 같아요. 연락 test@example.test 010-1234-5678 https://example.test/id",
                "author": "original-author",
                "thread": "original-thread",
                "rating": 4,
            },
            {
                "local_id": "original-id-two",
                "reply_to_id": "original-id-one",
                "text": "서비스가 좋나요?",
                "author": "original-author",
                "rating": 5,
            },
            {
                "local_id": "original-id-three",
                "text": "=1+1 <script>window.bad=1</script>",
                "author": "second-author",
            },
        ],
    }


def create(server):
    response = server.post("/api/datasets", payload(), headers=KEY)
    assert response.status_code == 201, response.text
    return response.json()


def analyse(server, data):
    response = server.post(
        f"/api/datasets/{data['dataset_id']}/analyze", headers=KEY, stream=True
    )
    assert response.status_code == 200, response.text
    return list(frames(response))


class DatasetHTTPTests(unittest.TestCase):
    def test_private_redacted_upload_and_validation(self):
        with LiveServer() as server:
            self.assertEqual(server.post("/api/datasets", payload()).status_code, 401)
            invalid = payload()
            invalid["reviewed"] = False
            self.assertEqual(
                server.post("/api/datasets", invalid, headers=KEY).status_code, 422
            )
            data = create(server)
            serialized = json.dumps(data, ensure_ascii=False)
            for value in [
                "test@example.test",
                "010-1234-5678",
                "https://example.test/id",
                "original-author",
                "original-thread",
                "original-id-one",
                "a" * 64,
                "lease",
            ]:
                self.assertNotIn(value, serialized)
            self.assertIn("[이메일]", serialized)
            self.assertEqual(data["reply_pairs"], 1)
            self.assertEqual(data["rows"][0]["author"], data["rows"][1]["author"])
            self.assertEqual(data["basic"]["count"], 3)
            self.assertEqual(data["ai"]["analysed"], 0)
            url = f"/api/datasets/{data['dataset_id']}"
            self.assertEqual(server.get(url).status_code, 401)
            self.assertEqual(server.get(url + "?format=json").status_code, 401)
            self.assertEqual(
                server.post(
                    "/api/datasets", payload(), headers={"X-Dataset-Key": "bad"}
                ).status_code,
                401,
            )
            self.assertEqual(
                requests.get(server.base + url, headers=OTHER, timeout=10).status_code,
                404,
            )
            response = requests.get(server.base + url, headers=KEY, timeout=10)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(
                requests.get(
                    server.base + "/api/datasets", headers=OTHER, timeout=10
                ).json(),
                [],
            )
            with sqlite3.connect(server.db) as db:
                raw, owner = db.execute("SELECT payload,owner FROM datasets").fetchone()
            self.assertNotIn("original-author", raw)
            self.assertNotEqual(owner, "a" * 64)

    def test_analysis_same_contract_checkpoint_and_no_double_charge(self):
        with LiveServer() as server:
            data = create(server)
            events = analyse(server, data)
            self.assertEqual(
                [kind for kind, _ in events], ["start", "row", "row", "row", "complete"]
            )
            finished = events[-1][1]
            self.assertEqual(finished["ai"]["analysed"], 3)
            self.assertEqual(server.units(), 3)
            self.assertTrue(
                all(row["analysis_version"] == "text-v1" for row in finished["rows"])
            )
            self.assertEqual(
                [kind for kind, _ in analyse(server, data)], ["start", "complete"]
            )
            self.assertEqual(server.units(), 3)

    def test_partial_quota_resumes_after_restart(self):
        with LiveServer(LLM_DAILY_UNIT_CAP="2") as server:
            data = create(server)
            events = analyse(server, data)
            self.assertEqual(events[-1][0], "error")
            self.assertEqual(events[-1][1]["status"], 429)
            saved = requests.get(
                server.base + f"/api/datasets/{data['dataset_id']}",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertEqual(saved["ai"]["analysed"], 2)
            self.assertEqual(server.units(), 2)
            exported = requests.get(
                server.base
                + f"/api/datasets/{data['dataset_id']}/export?format=json&completed_only=true",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertEqual(len(exported["dataset"]["rows"]), 2)
            self.assertEqual(exported["total_dataset_rows"], 3)
            server.stop()
            server.env["LLM_DAILY_UNIT_CAP"] = "5"
            server.start()
            self.assertEqual(analyse(server, data)[-1][1]["ai"]["analysed"], 3)
            self.assertEqual(server.units(), 3)

    def test_failed_rows_attempt_once_then_resume(self):
        with LiveServer(FAKE_PARSE_FAIL="true") as server:
            data = create(server)
            result = analyse(server, data)[-1][1]
            self.assertEqual(result["ai"]["analysed"], 0)
            self.assertTrue(all(row["status"] == "failed" for row in result["rows"]))
            self.assertEqual(server.units(), 3)
            server.stop()
            server.env["FAKE_PARSE_FAIL"] = "false"
            server.start()
            self.assertEqual(analyse(server, data)[-1][1]["ai"]["analysed"], 3)
            self.assertEqual(server.units(), 6)

    def test_cancel_retains_completed_rows_and_resume_skips_them(self):
        with LiveServer(FAKE_PARSE_DELAY=".4") as server:
            data = create(server)
            response = server.post(
                f"/api/datasets/{data['dataset_id']}/analyze", headers=KEY, stream=True
            )
            for kind, _ in frames(response):
                if kind == "row":
                    break
            response.close()
            time.sleep(0.6)
            saved = requests.get(
                server.base + f"/api/datasets/{data['dataset_id']}",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertGreaterEqual(saved["ai"]["analysed"], 1)
            self.assertLess(saved["ai"]["analysed"], 3)
            result = analyse(server, data)[-1][1]
            self.assertEqual(result["ai"]["analysed"], 3)
            self.assertEqual(server.units(), 3)

    def test_linked_village_privacy_comparison_exports_and_delete(self):
        import requests

        with LiveServer() as server:
            data = create(server)
            data = analyse(server, data)[-1][1]
            run = server.post(
                "/api/runs",
                {
                    "dataset_id": data["dataset_id"],
                    "dataset_row_id": data["rows"][0]["row_id"],
                    "steps": 2,
                    "engine": "openai",
                },
                headers=KEY,
            )
            self.assertEqual(run.status_code, 201, run.text)
            run = run.json()
            self.assertEqual(run["topic"], data["rows"][0]["text"])
            self.assertEqual(
                run["source_data"]["analysis"], data["rows"][0]["analysis"]
            )
            self.assertEqual(server.get("/api/runs/" + run["run_id"]).status_code, 404)
            self.assertNotIn(
                run["run_id"], [r["run_id"] for r in server.get("/api/runs").json()]
            )
            self.assertEqual(
                requests.get(
                    server.base + "/api/runs/" + run["run_id"],
                    headers=OTHER,
                    timeout=10,
                ).status_code,
                404,
            )
            self.assertEqual(
                requests.get(
                    server.base + "/api/runs/" + run["run_id"], headers=KEY, timeout=10
                ).json(),
                run,
            )
            self.assertEqual(server.units(), 7)
            result = requests.get(
                server.base
                + f"/api/datasets/{data['dataset_id']}/compare?run_id={run['run_id']}",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertTrue(result["ai"]["comparable"])
            self.assertEqual(result["basic"]["real"]["count"], 3)
            self.assertEqual(result["basic"]["virtual"]["count"], 2)
            for format in ["csv", "json", "html"]:
                response = requests.get(
                    server.base
                    + f"/api/datasets/{data['dataset_id']}/export?format={format}&run_id={run['run_id']}",
                    headers=KEY,
                    timeout=10,
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn("attachment", response.headers["Content-Disposition"])
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertNotIn("a" * 64, response.text)
                if format == "csv":
                    rows = list(
                        csv.DictReader(
                            io.StringIO(response.content.decode("utf-8-sig"))
                        )
                    )
                    self.assertEqual(len(rows), 3)
                    self.assertTrue(rows[2]["text"].startswith("'="))
                elif format == "json":
                    self.assertEqual(response.json()["comparison"], result)
                else:
                    self.assertNotIn("<script>", response.text)
                    self.assertIn("&lt;script&gt;", response.text)
                    self.assertIn('class="track"', response.text)
                    self.assertIn("Content-Security-Policy", response.text)
            self.assertEqual(
                requests.delete(
                    server.base + f"/api/datasets/{data['dataset_id']}",
                    headers=OTHER,
                    timeout=10,
                ).status_code,
                404,
            )
            self.assertEqual(
                requests.delete(
                    server.base + f"/api/datasets/{data['dataset_id']}",
                    headers=KEY,
                    timeout=10,
                ).status_code,
                204,
            )
            self.assertEqual(
                requests.get(
                    server.base + "/api/runs/" + run["run_id"], headers=KEY, timeout=10
                ).status_code,
                404,
            )

    def test_rules_comparison_does_not_invent_ai_analysis(self):
        import requests

        with LiveServer() as server:
            data = create(server)
            run = server.post(
                "/api/runs",
                {
                    "dataset_id": data["dataset_id"],
                    "dataset_row_id": data["rows"][0]["row_id"],
                    "steps": 1,
                },
                headers=KEY,
            ).json()
            result = requests.get(
                server.base
                + f"/api/datasets/{data['dataset_id']}/compare?run_id={run['run_id']}",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertFalse(result["ai"]["comparable"])
            self.assertEqual(result["ai"]["virtual"]["analysed"], 0)
            self.assertEqual(
                requests.post(
                    server.base + "/api/runs",
                    json={
                        "dataset_id": data["dataset_id"],
                        "dataset_row_id": data["rows"][0]["row_id"],
                        "steps": 1,
                    },
                    timeout=10,
                ).status_code,
                401,
            )
            self.assertEqual(server.units(), 0)

    def test_concurrent_analysis_does_not_double_bill_rows(self):
        import concurrent.futures

        with LiveServer(FAKE_PARSE_DELAY=".2") as server:
            data = create(server)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                events = list(pool.map(lambda _: analyse(server, data), range(2)))
            self.assertTrue(all(result[-1][0] == "complete" for result in events))
            saved = requests.get(
                server.base + f"/api/datasets/{data['dataset_id']}",
                headers=KEY,
                timeout=10,
            ).json()
            self.assertEqual(saved["ai"]["analysed"], 3)
            self.assertEqual(server.units(), 3)

    def test_source_deleted_during_run_cannot_be_persisted(self):
        with LiveServer(FAKE_PARSE_DELAY=".4") as server:
            data = create(server)
            response = server.post(
                "/api/runs/stream",
                {
                    "dataset_id": data["dataset_id"],
                    "dataset_row_id": data["rows"][0]["row_id"],
                    "steps": 3,
                    "engine": "openai",
                },
                headers=KEY,
                stream=True,
            )
            iterator = frames(response)
            for kind, _ in iterator:
                if kind == "step":
                    break
            self.assertEqual(
                requests.delete(
                    server.base + f"/api/datasets/{data['dataset_id']}",
                    headers=KEY,
                    timeout=10,
                ).status_code,
                204,
            )
            remaining = list(iterator)
            self.assertEqual(remaining[-1][0], "error")
            self.assertEqual(remaining[-1][1]["status"], 404)
            self.assertEqual(
                requests.get(server.base + "/api/runs", headers=KEY, timeout=10).json(),
                [],
            )
            self.assertLessEqual(server.units(), 2)

    def test_legacy_batch_analysis_signature_is_fixed_and_charged(self):
        with LiveServer() as server:
            count = len(server.get("/ingest/messages").json())
            response = server.post("/analysis/messages")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["success_count"], count)
            self.assertEqual(server.units(), count)
