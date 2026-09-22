from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)
from openai import OpenAIError

from app.routers.agents import agents
from app.routers.memories import memories
from app.services.reflection import (
    generate_reflections,
)
from app.services.storage import save_memories


router = APIRouter(
    prefix="/agents",
    tags=["Reflections"],
)


def find_agent(agent_id: str):
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent

    return None


@router.post("/{agent_id}/reflect")
def reflect_on_memories(
    agent_id: str,
    threshold: int = Query(
        default=20,
        ge=5,
        le=100,
        description=(
            "반추를 실행할 기억 중요도 임계치"
        ),
    ),
):
    agent = find_agent(agent_id)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail="에이전트를 찾을 수 없습니다.",
        )

    agent_memories = [
        memory
        for memory in memories
        if memory.agent_id == agent_id
    ]

    try:
        result = generate_reflections(
            agent=agent,
            agent_memories=agent_memories,
            importance_threshold=threshold,
        )

    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"OpenAI API 반추 실패: {error}"
            ),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    new_memories = result["new_memories"]

    if new_memories:
        memories.extend(new_memories)
        save_memories(memories)

    return {
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        **result,
    }