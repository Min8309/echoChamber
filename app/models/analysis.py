from enum import Enum

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class Certainty(str, Enum):
    confirmed = "confirmed"
    hearsay = "hearsay"
    speculation = "speculation"


class DialogueAnalysisRequest(BaseModel):
    text: str = Field(
        min_length=1,
        description="분석할 대화 문장",
    )
    speaker_name: str = Field(
        min_length=1,
        description="말한 에이전트 이름",
    )
    listener_name: str = Field(
        min_length=1,
        description="들은 에이전트 이름",
    )


class DialogueAnalysis(BaseModel):
    is_gossip: bool
    subject: str | None
    claim: str
    sentiment: Sentiment
    certainty: Certainty
    confidence: float = Field(ge=0.0, le=1.0)
    reputation_impact: float = Field(ge=-1.0, le=1.0)
    reason: str