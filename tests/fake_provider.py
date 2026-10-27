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
