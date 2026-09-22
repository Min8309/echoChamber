from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class MessageSource(str, Enum):
    naver_comment = "naver_comment"
    anonymous_board = "anonymous_board"
    messenger = "messenger"
    manual = "manual"


class RealMessageCreate(BaseModel):
    message_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)

    source_type: MessageSource = (
        MessageSource.naver_comment
    )

    author_id: str = Field(min_length=1)
    reply_to_id: str | None = None

    text: str = Field(
        min_length=1,
        description="분석할 댓글 또는 대화 내용",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class RealMessage(RealMessageCreate):
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class MessageBatchRequest(BaseModel):
    messages: list[RealMessageCreate] = Field(
        min_length=1,
        max_length=500,
    )


class MessageBatchResponse(BaseModel):
    requested_count: int
    saved_count: int
    duplicate_count: int
    messages: list[RealMessage]