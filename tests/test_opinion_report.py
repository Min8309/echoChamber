import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.services.opinion_report import build_report, source_comparison, SourceComparison
from test_datasets import KEY, OTHER, create, payload
from test_protection import LiveServer


class OpinionReportTests(unittest.TestCase):
    def test_sample_statistics_and_missing_data(self):
        rows = [
            {"row_id": "a", "number": 1, "text": "아마 좋을 것 같아요", "date": "2026-10-27", "analysis": {
                "claim": "행사 환영", "sentiment": "positive", "certainty": "speculation"}},
            {"row_id": "b", "number": 2, "text": "무조건 최고", "reply_to_id": "a", "date": "2026-10-28", "analysis": {
                "claim": "행사 환영", "sentiment": "positive", "certainty": "confirmed"}},
            {"row_id": "c", "number": 3, "text": "다른 의견", "analysis": None},
        ]
        report = build_report({"dataset_id": "sample", "title": "행사", "rows": rows})
        sections = report["sections"]
        self.assertEqual([s["number"] for s in sections], list(range(1, 11)))
        self.assertEqual(sections[1]["result"][0]["댓글 수"], 2)
        self.assertIsNone(sections[2]["result"])
        self.assertEqual(sections[3]["result"]["추측"]["비율(%)"], 33.3)
        self.assertEqual(sections[4]["result"]["분포"]["긍정"]["비율(%)"], 100)
        self.assertEqual(sections[4]["result"]["미분석"], 1)
        self.assertEqual(sections[5]["result"][0]["AI 분류 변화"]["certainty"]["답글"], "confirmed")
        self.assertEqual(len(sections[6]["result"]), 2)
        self.assertEqual(len(sections[7]["result"]), 2)

    def test_unanalysed_is_not_zero_sentiment(self):
        report = build_report({"dataset_id": "sample", "title": "행사", "rows": [
            {"row_id": "a", "number": 1, "text": "안녕하세요"}]})
        self.assertIsNone(report["sections"][4]["result"]["분포"]["중립"]["비율(%)"])
        self.assertEqual(report["sections"][6]["result"], [])

    def test_ai_evidence_validation_and_client_cleanup(self):
        for row_id, valid in [("a", True), ("invented", False)]:
            result = SourceComparison(summary="행사 공지", novel_claims=[
                {"text": "취소 주장", "row_ids": [row_id]}], opposing_views=[])
            client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(output_parsed=result)), close=unittest.mock.Mock())
            with patch("app.services.opinion_report.get_ai_client", return_value=client):
                if valid:
                    self.assertEqual(source_comparison([{"row_id": "a", "text": "취소"}], "공지")["summary"], "행사 공지")
                else:
                    with self.assertRaises(ValueError):
                        source_comparison([{"row_id": "a", "text": "취소"}], "공지")
                client.close.assert_called_once()

    def test_http_ownership_no_key_and_redaction(self):
        with LiveServer(ECHOCHAMBER_API_KEY="", OPENAI_API_KEY="") as server:
            data = create(server)
            path = f'/api/datasets/{data["dataset_id"]}/opinion-report'
            self.assertEqual(server.post(path, headers=OTHER).status_code, 404)
            self.assertEqual(server.post(path).status_code, 401)
            response = server.post(path, {"source_text": "문의 user@example.test"}, headers=KEY)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["sections"]), 10)
            self.assertNotIn("user@example.test", response.text)
            self.assertEqual(server.units(), 0)
            self.assertEqual(server.post(path, {"use_ai": True}, headers=KEY).status_code, 422)
            self.assertEqual(server.post(path, {"source_text": "공지", "use_ai": True}, headers=KEY).status_code, 409)

    def test_http_ai_failure_does_not_claim_completion(self):
        with LiveServer(FAKE_PARSE_FAIL="true") as server:
            data = create(server)
            response = server.post(f'/api/datasets/{data["dataset_id"]}/opinion-report',
                                   {"source_text": "공지", "use_ai": True}, headers=KEY)
            self.assertEqual(response.status_code, 502)
            self.assertEqual(server.units(), 1)


if __name__ == "__main__":
    unittest.main()
