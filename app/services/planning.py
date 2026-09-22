import os

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from app.models.agent import Agent
from app.models.memory import Memory, MemoryType
from app.models.planning import AgentPlan
from app.services.retrieval import retrieve_memories


load_dotenv()


def generate_agent_plan(
    agent: Agent,
    candidate_agents: list[Agent],
    agent_memories: list[Memory],
) -> dict:
    if not candidate_agents:
        raise ValueError(
            "계획 대상이 될 다른 에이전트가 없습니다."
        )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다."
        )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-astra",
    )

    retrieved_results = retrieve_memories(
        agent_memories=agent_memories,
        query=(
            f"{agent.current_goal}을 달성하기 위한 "
            "다음 대화와 행동 계획"
        ),
        top_k=6,
    )

    retrieved_memories = [
        result["memory"]
        for result in retrieved_results
    ]

    if retrieved_memories:
        memory_text = "\n".join(
            (
                f"- 기억 ID: {memory.memory_id}\n"
                f"  유형: {memory.memory_type.value}\n"
                f"  내용: {memory.description}\n"
                f"  중요도: {memory.importance}\n"
                f"  신뢰도: {memory.confidence}"
            )
            for memory in retrieved_memories
        )
    else:
        memory_text = "회상된 기억이 없습니다."

    candidate_text = "\n".join(
        (
            f"- ID: {candidate.agent_id}\n"
            f"  이름: {candidate.name}\n"
            f"  직업: {candidate.occupation}\n"
            f"  현재 위치: {candidate.current_location}\n"
            f"  사교성: "
            f"{candidate.personality.sociability}\n"
            f"  소문 신뢰 성향: "
            f"{candidate.personality.credulity}"
        )
        for candidate in candidate_agents
    )

    instructions = """
당신은 가상 마을 에이전트의 계획 생성 엔진이다.

에이전트의 목표, 성격, 기억과 대화 가능한 상대를
분석하여 다음 대화 계획 하나를 생성한다.

규칙:
1. 반드시 제공된 대상 에이전트 ID 중 하나만 선택한다.
2. 기억에 없는 사실을 새롭게 만들지 않는다.
3. 현재 목표 달성에 도움이 되는 계획을 우선한다.
4. 신뢰도가 낮은 기억은 사실로 단정하지 않는다.
5. 소문을 확인하려는 경우 verify_rumor를 사용한다.
6. 정보를 전달하려는 경우 share_information을 사용한다.
7. 대상과 친해지려는 경우 build_relationship을 사용한다.
8. 대화 주제는 자연스러운 한국어 문장으로 작성한다.
"""

    prompt = f"""
[계획을 세우는 에이전트]
ID: {agent.agent_id}
이름: {agent.name}
직업: {agent.occupation}
현재 위치: {agent.current_location}
현재 목표: {agent.current_goal}
사교성: {agent.personality.sociability}
가십 성향: {agent.personality.gossip_tendency}
소문 신뢰 성향: {agent.personality.credulity}

[회상된 기억]
{memory_text}

[대화 가능한 에이전트]
{candidate_text}

위 정보를 바탕으로 다음에 누구와 어떤 주제로
대화할 것인지 하나의 계획을 생성하라.
"""

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.parse(
            model=model,
            reasoning={
                "effort": "low",
            },
            input=[
                {
                    "role": "system",
                    "content": instructions,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=AgentPlan,
        )

    except OpenAIError as error:
        raise RuntimeError(
            f"Planning API 호출 실패: {error}"
        ) from error

    plan = response.output_parsed

    if plan is None:
        raise ValueError(
            "OpenAI API가 계획을 반환하지 않았습니다."
        )

    valid_target_ids = {
        candidate.agent_id
        for candidate in candidate_agents
    }

    if plan.target_agent_id not in valid_target_ids:
        raise ValueError(
            "Planning 결과에 존재하지 않는 "
            "대상 agent_id가 포함되었습니다."
        )

    target_agent = next(
        candidate
        for candidate in candidate_agents
        if candidate.agent_id
        == plan.target_agent_id
    )

    plan_memory = Memory(
        agent_id=agent.agent_id,
        memory_type=MemoryType.plan,
        description=(
            f"{agent.name}의 계획: "
            f"{target_agent.name}에게 "
            f"'{plan.topic}'에 관해 대화한다. "
            f"행동 목적은 {plan.action.value}이다. "
            f"계획 이유: {plan.reason}"
        ),
        importance=plan.priority,
        source_agent_id=None,
        subject_agent_ids=[
            target_agent.agent_id
        ],
        evidence_memory_ids=[
            memory.memory_id
            for memory in retrieved_memories
        ],
        confidence=1.0,
    )

    return {
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        "target_agent": {
            "agent_id": target_agent.agent_id,
            "name": target_agent.name,
        },
        "plan": plan,
        "retrieved_memory_ids": [
            memory.memory_id
            for memory in retrieved_memories
        ],
        "plan_memory": plan_memory,
    }