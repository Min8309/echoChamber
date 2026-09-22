import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models.agent import Agent
from app.models.memory import (
    Memory,
    MemoryType,
)
from app.models.reflection import (
    ReflectionOutput,
)


load_dotenv()

client = OpenAI()


def generate_reflections(
    agent: Agent,
    agent_memories: list[Memory],
    importance_threshold: int = 20,
    recent_limit: int = 20,
):
    ordered_memories = sorted(
        agent_memories,
        key=lambda memory: memory.created_at,
    )

    reflection_memories = [
        memory
        for memory in ordered_memories
        if (
            memory.memory_type
            == MemoryType.reflection
        )
    ]

    latest_reflection_time = None

    if reflection_memories:
        latest_reflection_time = (
            reflection_memories[-1].created_at
        )

    candidate_memories = [
        memory
        for memory in ordered_memories
        if (
            memory.memory_type
            != MemoryType.reflection
            and (
                latest_reflection_time is None
                or memory.created_at
                > latest_reflection_time
            )
        )
    ]

    importance_sum = sum(
        memory.importance
        for memory in candidate_memories
    )

    if len(candidate_memories) < 3:
        return {
            "triggered": False,
            "reason": (
                "반추에 필요한 기억이 "
                "3개 미만입니다."
            ),
            "importance_sum": importance_sum,
            "new_memories": [],
        }

    if importance_sum < importance_threshold:
        return {
            "triggered": False,
            "reason": (
                "최근 기억의 중요도 합이 "
                "임계치보다 낮습니다."
            ),
            "importance_sum": importance_sum,
            "new_memories": [],
        }

    evidence_memories = candidate_memories[
        -recent_limit:
    ]

    memory_lines = []

    for index, memory in enumerate(
        evidence_memories,
        start=1,
    ):
        memory_lines.append(
            f"[{index}] "
            f"유형={memory.memory_type.value} | "
            f"중요도={memory.importance} | "
            f"내용={memory.description}"
        )

    memory_text = "\n".join(
        memory_lines
    )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-astra",
    )

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "너는 가상 마을 에이전트의 "
                    "경험을 반추하는 인지 엔진이다. "
                    "여러 기억에서 반복되는 행동, "
                    "관계, 동기, 평판 변화를 찾아 "
                    "1개에서 3개의 고차원 통찰을 "
                    "한국어로 작성한다. "
                    "단순히 기억을 복사하지 말고 "
                    "기억들을 종합한 결론을 만든다. "
                    "각 통찰에는 근거가 된 기억의 "
                    "번호를 evidence_indexes에 넣는다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"에이전트 이름: {agent.name}\n"
                    f"직업: {agent.occupation}\n"
                    f"현재 목표: {agent.current_goal}\n\n"
                    f"최근 기억:\n{memory_text}"
                ),
            },
        ],
        text_format=ReflectionOutput,
    )

    parsed = response.output_parsed

    if parsed is None:
        raise RuntimeError(
            "AI 반추 결과를 구조화하지 "
            "못했습니다."
        )

    new_memories = []

    for insight in parsed.insights:
        valid_indexes = sorted(
            {
                index
                for index
                in insight.evidence_indexes
                if (
                    1
                    <= index
                    <= len(evidence_memories)
                )
            }
        )

        if not valid_indexes:
            valid_indexes = list(
                range(
                    1,
                    min(
                        3,
                        len(evidence_memories),
                    )
                    + 1,
                )
            )

        selected_memories = [
            evidence_memories[index - 1]
            for index in valid_indexes
        ]

        evidence_memory_ids = [
            memory.memory_id
            for memory in selected_memories
        ]

        subject_agent_ids = list(
            dict.fromkeys(
                subject_id
                for memory
                in selected_memories
                for subject_id
                in memory.subject_agent_ids
            )
        )

        reflection_memory = Memory(
            agent_id=agent.agent_id,
            memory_type=MemoryType.reflection,
            description=insight.description,
            importance=insight.importance,
            source_agent_id=None,
            subject_agent_ids=(
                subject_agent_ids
            ),
            evidence_memory_ids=(
                evidence_memory_ids
            ),
            confidence=insight.confidence,
        )

        new_memories.append(
            reflection_memory
        )

    return {
        "triggered": True,
        "reason": "반추가 실행됐습니다.",
        "importance_sum": importance_sum,
        "new_memories": new_memories,
    }