from datetime import datetime, timezone
import re

from app.models.memory import Memory


RECENCY_WEIGHT = 0.3
IMPORTANCE_WEIGHT = 0.3
RELEVANCE_WEIGHT = 0.4
DECAY_FACTOR = 0.995


def calculate_recency(memory: Memory) -> float:
    now = datetime.now(timezone.utc)

    elapsed_seconds = (
        now - memory.last_accessed_at
    ).total_seconds()

    elapsed_hours = max(elapsed_seconds / 3600, 0)

    score = DECAY_FACTOR ** elapsed_hours

    return round(score, 4)


def calculate_importance(memory: Memory) -> float:
    score = memory.importance / 10

    return round(score, 4)


def tokenize(text: str) -> list[str]:
    cleaned_text = re.sub(
        r"[^\w가-힣\s]",
        " ",
        text.lower(),
    )

    return [
        word
        for word in cleaned_text.split()
        if word
    ]


def calculate_relevance(
    memory: Memory,
    query: str,
) -> float:
    query_words = tokenize(query)

    if not query_words:
        return 0.0

    description = memory.description.lower()

    matched_words = sum(
        1
        for word in query_words
        if word in description
    )

    score = matched_words / len(query_words)

    return round(score, 4)


def calculate_retrieval_score(
    memory: Memory,
    query: str,
) -> dict:
    recency = calculate_recency(memory)
    importance = calculate_importance(memory)
    relevance = calculate_relevance(
        memory,
        query,
    )

    total_score = (
        RECENCY_WEIGHT * recency
        + IMPORTANCE_WEIGHT * importance
        + RELEVANCE_WEIGHT * relevance
    )

    return {
        "memory": memory,
        "scores": {
            "recency": recency,
            "importance": importance,
            "relevance": relevance,
            "total": round(total_score, 4),
        },
    }


def retrieve_memories(
    agent_memories: list[Memory],
    query: str,
    top_k: int = 5,
) -> list[dict]:
    scored_memories = [
        calculate_retrieval_score(
            memory,
            query,
        )
        for memory in agent_memories
    ]

    scored_memories.sort(
        key=lambda item: item["scores"]["total"],
        reverse=True,
    )

    return scored_memories[:top_k]