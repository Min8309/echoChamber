from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.routers.agents import agents
from app.routers.memories import memories
from app.services.planning import (
    generate_agent_plan,
)
from app.services.storage import save_memories


router = APIRouter(
    prefix="/planning",
    tags=["Planning"],
)


def find_agent(agent_id: str):
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent

    return None


@router.post(
    "/{agent_id}",
    status_code=status.HTTP_201_CREATED,
)
def create_agent_plan(agent_id: str):
    agent = find_agent(agent_id)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail="에이전트를 찾을 수 없습니다.",
        )

    candidate_agents = [
        candidate
        for candidate in agents
        if candidate.agent_id != agent_id
    ]

    agent_memories = [
        memory
        for memory in memories
        if memory.agent_id == agent_id
    ]

    try:
        result = generate_agent_plan(
            agent=agent,
            candidate_agents=candidate_agents,
            agent_memories=agent_memories,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    memories.append(
        result["plan_memory"]
    )

    save_memories(memories)

    return result