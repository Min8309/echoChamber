import os

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from app.models.agent import Agent
from app.models.memory import Memory, MemoryType
from app.services.retrieval import retrieve_memories


load_dotenv()


def generate_ai_utterance(
    speaker: Agent,
    listener: Agent,
    topic: str,
    retrieved_memories: list[Memory],
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다."
        )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-astra",
    )

    client = OpenAI(api_key=api_key)

    memory_text = "\n".join(
        f"- {memory.description}"
        for memory in retrieved_memories
    )

    instructions = """
당신은 가상 마을 시뮬레이션의 대화 생성 엔진이다.

말하는 에이전트의 성격, 목표와 기억을 바탕으로
듣는 에이전트에게 할 자연스러운 한국어 발화를 생성한다.

규칙:
1. 제공되지 않은 새로운 사실을 함부로 만들지 않는다.
2. 에이전트의 기억을 대화체로 자연스럽게 표현한다.
3. 반드시 한두 문장으로 짧게 작성한다.
4. 설명이나 따옴표 없이 실제 발화만 출력한다.
5. 기억의 확실성이 낮으면 '들었는데', '그렇다더라'처럼 표현한다.
6. 응답을 비워 두지 말고 반드시 실제 발화를 출력한다.
"""

    prompt = f"""
[말하는 에이전트]
이름: {speaker.name}
직업: {speaker.occupation}
현재 목표: {speaker.current_goal}
사교성: {speaker.personality.sociability}
가십 성향: {speaker.personality.gossip_tendency}
소문 신뢰 성향: {speaker.personality.credulity}

[듣는 에이전트]
이름: {listener.name}
직업: {listener.occupation}

[현재 대화 주제]
{topic}

[회상된 기억]
{memory_text}

위 정보를 사용해 {speaker.name}가
{listener.name}에게 말할 자연스러운 한국어 발화를 생성하라.
"""

    max_attempts = 3
    last_status = None
    last_incomplete_details = None

    for attempt in range(1, max_attempts + 1):
        retry_message = ""

        if attempt > 1:
            retry_message = (
                "\n\n이전 요청에서 실제 발화가 생성되지 않았다. "
                "이번에는 반드시 한국어 발화 한두 문장만 출력하라."
            )

        try:
            response = client.responses.create(
                model=model,
                reasoning={
                    "effort": "low",
                },
                instructions=instructions,
                input=prompt + retry_message,
                max_output_tokens=500,
            )

        except OpenAIError as error:
            raise ValueError(
                f"OpenAI API 호출 실패: {error}"
            ) from error

        utterance = (
            response.output_text or ""
        ).strip()

        if utterance:
            return utterance

        last_status = getattr(
            response,
            "status",
            None,
        )

        last_incomplete_details = getattr(
            response,
            "incomplete_details",
            None,
        )

    raise ValueError(
        "OpenAI API가 3회 연속 빈 대화를 반환했습니다. "
        f"status={last_status}, "
        f"incomplete_details={last_incomplete_details}"
    )


def generate_conversation(
    speaker: Agent,
    listener: Agent,
    topic: str,
    speaker_memories: list[Memory],
) -> dict:
    retrieved_results = retrieve_memories(
        agent_memories=speaker_memories,
        query=topic,
        top_k=3,
    )

    if not retrieved_results:
        raise ValueError(
            "대화에 사용할 기억이 없습니다."
        )

    retrieved_memories = [
        result["memory"]
        for result in retrieved_results
    ]

    selected_memory = retrieved_memories[0]

    utterance = generate_ai_utterance(
        speaker=speaker,
        listener=listener,
        topic=topic,
        retrieved_memories=retrieved_memories,
    )

    listener_memory = Memory(
        agent_id=listener.agent_id,
        memory_type=MemoryType.dialogue,
        description=(
            f"{speaker.name}가 말했다: "
            f"{utterance}"
        ),
        importance=max(
            selected_memory.importance - 1,
            1,
        ),
        source_agent_id=speaker.agent_id,
        subject_agent_ids=(
            selected_memory.subject_agent_ids
        ),
        evidence_memory_ids=[
            selected_memory.memory_id
        ],
        confidence=round(
            selected_memory.confidence * 0.9,
            2,
        ),
    )

    return {
        "speaker_id": speaker.agent_id,
        "listener_id": listener.agent_id,
        "topic": topic,
        "utterance": utterance,
        "retrieved_memory_ids": [
            memory.memory_id
            for memory in retrieved_memories
        ],
        "listener_memory": listener_memory,
    }