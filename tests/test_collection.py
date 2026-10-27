import csv
import io
import json
import sqlite3
import time
import unittest
from unittest.mock import patch

import requests
from fastapi import HTTPException
from test_protection import LiveServer
from test_datasets import KEY, OTHER


class CollectionHTTPTests(unittest.TestCase):
    def test_youtube_replies_privacy_signed_provenance_and_exports(self):
        with LiveServer(
            FAKE_COLLECTION="true", YOUTUBE_API_KEY="test-only-source-key"
        ) as server:
            response = server.post(
                "/api/collection/preview",
                {
                    "provider": "youtube",
                    "video": "https://youtu.be/abcdefghijk",
                    "limit": 4,
                },
                headers=KEY,
            )
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result["origin"]["requests_used"], 3)
            self.assertEqual(len(result["rows"]), 4)
            serialized = json.dumps(result, ensure_ascii=False)
            for raw in [
                "private-top-1",
                "private-channel-A",
                "test-only-source-key",
                "test@example.test",
                "010-1234-5678",
            ]:
                self.assertNotIn(raw, serialized)
            self.assertEqual(
                result["rows"][1]["reply_to_id"], result["rows"][0]["local_id"]
            )
            self.assertEqual(
                result["rows"][2]["reply_to_id"], result["rows"][0]["local_id"]
            )
            self.assertLessEqual(
                result["origin"]["expires_at"] - time.time(), 30 * 86400
            )
            body = {
                "title": "실제 댓글",
                "source": "comment",
                "reviewed": True,
                "rows": result["rows"],
                "collection_token": result["collection_token"],
            }
            bad = server.post("/api/datasets", body, headers=OTHER)
            self.assertEqual(bad.status_code, 400)
            body["collection_token"] += "tamper"
            self.assertEqual(
                server.post("/api/datasets", body, headers=KEY).status_code, 400
            )
            body["collection_token"] = result["collection_token"]
            saved = server.post("/api/datasets", body, headers=KEY)
            self.assertEqual(saved.status_code, 201, saved.text)
            data = saved.json()
            self.assertEqual(data["reply_pairs"], 2)
            self.assertEqual(data["origin"]["provider"], "youtube")
            run = server.post(
                "/api/runs",
                {
                    "dataset_id": data["dataset_id"],
                    "dataset_row_id": data["rows"][0]["row_id"],
                    "steps": 1,
                },
                headers=KEY,
            ).json()
            self.assertEqual(server.units(), 0)
            with sqlite3.connect(server.db) as db:
                db.execute("UPDATE dataset_expiry SET expires_at = 0")
            self.assertEqual(
                requests.get(
                    server.base + "/api/runs/" + run["run_id"], headers=KEY, timeout=10
                ).status_code,
                404,
            )
            self.assertEqual(
                requests.get(
                    server.base + "/api/datasets/" + data["dataset_id"],
                    headers=KEY,
                    timeout=10,
                ).status_code,
                404,
            )
            with sqlite3.connect(server.db) as db:
                self.assertEqual(
                    db.execute("SELECT count(*) FROM datasets").fetchone()[0], 0
                )

    def test_no_key_and_invalid_sources_never_fetch_arbitrary_urls(self):
        from app.services.collection import video_id

        for value in [
            "https://youtube.com.evil.test/watch?v=abcdefghijk",
            "https://localhost/abcdefghijk",
            "file:///etc/passwd",
            "https://www.youtube.com@evil.test/watch?v=abcdefghijk",
        ]:
            with self.assertRaises(HTTPException):
                video_id(value)
        self.assertEqual(
            video_id("https://www.youtube.com/shorts/abcdefghijk"), "abcdefghijk"
        )
        with LiveServer(
            FAKE_COLLECTION="true", YOUTUBE_API_KEY="", YOUTUBE_DATA_API_KEY=""
        ) as server:
            r = server.post(
                "/api/collection/preview",
                {"provider": "youtube", "video": "abcdefghijk"},
                headers=KEY,
            )
            self.assertEqual(r.status_code, 409)
            self.assertEqual(
                server.post(
                    "/api/collection/preview", {"provider": "khaters"}
                ).status_code,
                401,
            )
            self.assertEqual(
                server.post(
                    "/api/collection/preview", {"provider": "kold"}, headers=KEY
                ).status_code,
                422,
            )
            self.assertFalse(
                server.get("/api/collection/sources").json()["youtube_configured"]
            )

    def test_khaters_attribution_reference_labels_and_hourly_limit(self):
        with LiveServer(
            FAKE_COLLECTION="true", COLLECTION_REQUESTS_PER_HOUR="1"
        ) as server:
            preview = server.post(
                "/api/collection/preview",
                {"provider": "khaters", "limit": 3},
                headers=KEY,
            ).json()
            self.assertEqual(preview["origin"]["requests_used"], 2)
            self.assertEqual(preview["origin"]["license"], "CC BY 4.0")
            data = server.post(
                "/api/datasets",
                {
                    "title": "연구 표본",
                    "source": "comment",
                    "reviewed": True,
                    "rows": preview["rows"],
                    "collection_token": preview["collection_token"],
                },
                headers=KEY,
            ).json()
            self.assertEqual(data["rows"][0]["reference_labels"]["label"], "Normal")
            for format in ["csv", "json", "html"]:
                response = requests.get(
                    server.base
                    + f"/api/datasets/{data['dataset_id']}/export?format={format}",
                    headers=KEY,
                    timeout=10,
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("Park", response.content.decode("utf-8-sig"))
                self.assertIn("CC BY", response.content.decode("utf-8-sig"))
            self.assertEqual(server.units(), 0)
            limited = server.post(
                "/api/collection/preview", {"provider": "khaters"}, headers=KEY
            )
            self.assertEqual(limited.status_code, 429)

    def test_collection_daily_call_cap(self):
        with LiveServer(
            FAKE_COLLECTION="true", COLLECTION_DAILY_CALL_CAP="1"
        ) as server:
            response = server.post(
                "/api/collection/preview", {"provider": "khaters"}, headers=KEY
            )
            self.assertEqual(response.status_code, 429)
            with sqlite3.connect(server.db) as db:
                self.assertEqual(
                    db.execute("SELECT sum(units) FROM collection_calls").fetchone()[0],
                    1,
                )


class OfficialTransportTests(unittest.TestCase):
    def test_transport_keeps_key_out_of_url_and_maps_disabled_comments(self):
        from app.services.collection import OfficialHTTP

        response = requests.Response()
        response.status_code = 403
        response._content = json.dumps(
            {"error": {"errors": [{"reason": "commentsDisabled"}]}}
        ).encode()
        response._content_consumed = True
        with (
            patch("app.services.collection.quota"),
            patch("app.services.collection.requests.get", return_value=response) as get,
        ):
            with self.assertRaises(HTTPException) as error:
                OfficialHTTP().get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    {"videoId": "abcdefghijk"},
                    "test-only-key",
                )
            self.assertEqual(error.exception.status_code, 409)
            self.assertNotIn("key", get.call_args.kwargs["params"])
            self.assertEqual(
                get.call_args.kwargs["headers"]["X-Goog-Api-Key"], "test-only-key"
            )
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
