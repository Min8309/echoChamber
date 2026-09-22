from pydantic import BaseModel, Field

from app.models.analysis import DialogueAnalysis
from app.models.memory import Memory


class ConversationRequest(BaseModel):
    speaker_id: str
    listener_id: str

    topic: str = Field(
        min_length=1,
        description="현재 대화 주제",
    )


class ConversationResponse(BaseModel):
    speaker_id: str
    listener_id: str
    topic: str
    utterance: str
    retrieved_memory_ids: list[str]
    listener_memory: Memory
    analysis: DialogueAnalysis