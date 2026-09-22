from fastapi import APIRouter, HTTPException, status

from app.models.agent import Agent
from app.services.storage import (
    load_agents,
    save_agents,
)


router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
)

agents: list[Agent] = load_agents()


@router.post(
    "",
    response_model=Agent,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(agent: Agent):
    agents.append(agent)

    save_agents(agents)

    return agent


@router.get("", response_model=list[Agent])
def get_agents():
    return agents


@router.get("/{agent_id}", response_model=Agent)
def get_agent(agent_id: str):
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent

    raise HTTPException(
        status_code=404,
        detail="에이전트를 찾을 수 없습니다.",
    )