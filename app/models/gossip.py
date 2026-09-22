from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.analysis import DialogueAnalysis


class GossipEvent(BaseModel):
    event_id: str = Field(
        default_factory=lambda: str(uuid4())
    )
    speaker_id: str
    listener_id: str
    topic: str
    utterance: str
    analysis: DialogueAnalysis
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )