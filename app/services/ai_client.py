"""Create API clients only when an AI operation is requested."""

import os

from dotenv import load_dotenv
from openai import OpenAI


def get_ai_client() -> OpenAI:
    load_dotenv()
    key = os.getenv("ECHOCHAMBER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "AI 모드에는 ECHOCHAMBER_API_KEY 또는 OPENAI_API_KEY가 필요합니다."
        )
    return OpenAI(api_key=key, timeout=30, max_retries=0)
