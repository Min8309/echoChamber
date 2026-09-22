from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    observation = "observation"
    dialogue = "dialogue"
    reflection = "reflection"
    plan = "plan"

class MemoryCreate(BaseModel):
    memory_type: MemoryType

    description: str = Field(
        min_length=1,
        description="기억의 자연어 내용",
    )

    importance: int = Field(
        default=5,
        ge=1,
        le=10,
        description="기억의 중요도",
    )

    source_agent_id: str | None = None

    subject_agent_ids: list[str] = Field(
        default_factory=list
    )

    evidence_memory_ids: list[str] = Field(
        default_factory=list
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )


class Memory(MemoryCreate):
    memory_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    agent_id: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    last_accessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )