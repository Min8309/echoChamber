"""Create API clients only when an AI operation is requested."""

import os

from dotenv import load_dotenv
from openai import OpenAI
from app.services.limits import charge_llm_unit


def get_ai_client() -> "LimitedClient":
    load_dotenv()
    key = os.getenv("ECHOCHAMBER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "AI 모드에는 ECHOCHAMBER_API_KEY 또는 OPENAI_API_KEY가 필요합니다."
        )
    return LimitedClient(OpenAI(api_key=key, timeout=30, max_retries=0))


class LimitedResponses:
    def __init__(self, responses):
        self._responses = responses

    def create(self, **kwargs):
        charge_llm_unit()
        return self._responses.create(**kwargs)

    def parse(self, **kwargs):
        charge_llm_unit()
        return self._responses.parse(**kwargs)


class LimitedClient:
    def __init__(self, client):
        self._client = client
        self.responses = LimitedResponses(client.responses)

    def close(self):
        self._client.close()
