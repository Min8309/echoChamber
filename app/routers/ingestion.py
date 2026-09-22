import hashlib
import os

from fastapi import APIRouter, status

from app.models.message import (
    MessageBatchRequest,
    MessageBatchResponse,
    RealMessage,
)
from app.services.storage import (
    load_messages,
    save_messages,
)


router = APIRouter(
    prefix="/ingest",
    tags=["Real Message Ingestion"],
)


messages: list[RealMessage] = load_messages()


def pseudonymize_author(author_id: str) -> str:
    salt = os.getenv(
        "MESSAGE_HASH_SALT",
        "echochamber-development-salt",
    )

    value = f"{salt}:{author_id}"

    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

    return f"user_{digest[:16]}"


@router.post(
    "/messages",
    response_model=MessageBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_messages(
    request: MessageBatchRequest,
):
    existing_ids = {
        message.message_id
        for message in messages
    }

    saved_messages = []
    duplicate_count = 0

    for message_data in request.messages:
        if message_data.message_id in existing_ids:
            duplicate_count += 1
            continue

        data = message_data.model_dump()

        data["author_id"] = pseudonymize_author(
            message_data.author_id
        )

        message = RealMessage(**data)

        messages.append(message)
        saved_messages.append(message)
        existing_ids.add(message.message_id)

    if saved_messages:
        save_messages(messages)

    return MessageBatchResponse(
        requested_count=len(request.messages),
        saved_count=len(saved_messages),
        duplicate_count=duplicate_count,
        messages=saved_messages,
    )


@router.get(
    "/messages",
    response_model=list[RealMessage],
)
def get_ingested_messages():
    return messages