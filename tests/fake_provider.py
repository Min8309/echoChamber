"""Test-only SDK stand-in. It never opens network connections."""

import os
import time
from types import SimpleNamespace


class FakeResponses:
    def create(self, **kwargs):
        time.sleep(float(os.getenv("FAKE_CREATE_DELAY", ".01")))
        return SimpleNamespace(
            output_text="도서관 행사 소식을 들었어요. 아직 확인이 필요해요."
        )

    def parse(self, **kwargs):
        time.sleep(float(os.getenv("FAKE_PARSE_DELAY", ".01")))
        if os.getenv("FAKE_PARSE_FAIL") == "true":
            raise RuntimeError("Test-only provider failure")
        result = kwargs["text_format"].model_validate(
            {
                "is_gossip": True,
                "subject": "마을 행사",
                "claim": "도서관 행사 소식",
                "sentiment": "neutral",
                "certainty": "hearsay",
                "confidence": 0.65,
                "reputation_impact": -0.1,
                "reason": "테스트용 모의 AI 분석",
            }
        )
        return SimpleNamespace(output_parsed=result)


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.responses = FakeResponses()

    def close(self):
        pass


class FakeOfficialHTTP:
    """Test-only public-source adapter. No external requests or real API key."""

    def __init__(self):
        self.calls = 0

    def get(self, url, params, key=None):
        from app.services.collection import quota

        quota()
        self.calls += 1
        if url.endswith("/commentThreads"):
            return {
                "items": [
                    {
                        "snippet": {
                            "topLevelComment": {
                                "id": "private-top-1",
                                "snippet": {
                                    "textOriginal": "카페 소식이에요 test@example.test 010-1234-5678",
                                    "authorChannelId": {"value": "private-channel-A"},
                                    "publishedAt": "2026-10-27T00:00:00Z",
                                },
                            },
                            "totalReplyCount": 2,
                        }
                    },
                    {
                        "snippet": {
                            "topLevelComment": {
                                "id": "private-top-2",
                                "snippet": {
                                    "textOriginal": "둘째 댓글입니다",
                                    "authorChannelId": {"value": "private-channel-B"},
                                },
                            },
                            "totalReplyCount": 0,
                        }
                    },
                ]
            }
        if url.endswith("/comments"):
            page = params.get("pageToken")
            return {
                "items": [
                    {
                        "id": "private-reply-2" if page else "private-reply-1",
                        "snippet": {
                            "textOriginal": "답글입니다",
                            "authorChannelId": {"value": "private-channel-A"},
                            "parentId": params["parentId"],
                        },
                    }
                ],
                **({} if page else {"nextPageToken": "second-page"}),
            }
        if url.endswith("/splits"):
            return {
                "splits": [
                    {"config": "default", "split": split}
                    for split in ["train", "validation", "test"]
                ]
            }
        if url.endswith("/rows"):
            return {
                "rows": [
                    {
                        "row": {
                            "id": 100 + i,
                            "text": f"연구 댓글 표본 {i} test@example.test",
                            "label": "Normal",
                            "target_label": ["others"],
                        }
                    }
                    for i in range(min(params["length"], 3))
                ]
            }
        raise RuntimeError("Unrecognized test endpoint")
