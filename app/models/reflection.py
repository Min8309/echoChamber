from pydantic import BaseModel, Field


class ReflectionInsightDraft(BaseModel):
    description: str = Field(
        min_length=1,
    )

    importance: int = Field(
        ge=1,
        le=10,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence_indexes: list[int]


class ReflectionOutput(BaseModel):
    insights: list[
        ReflectionInsightDraft
    ] = Field(
        min_length=1,
        max_length=3,
    )