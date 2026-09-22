from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from app.models.memory import Memory, MemoryCreate
from app.routers.agents import agents
from app.services.retrieval import retrieve_memories
from app.services.storage import (
    load_memories,
    save_memories,
)


router = APIRouter(
    prefix="/agents",
    tags=["Memories"],
)

memories: list[Memory] = load_memories()


def agent_exists(agent_id: str) -> bool:
    return any(
        agent.agent_id == agent_id
        for agent in agents
    )


@router.post(
    "/{agent_id}/memories",
    response_model=Memory,
    status_code=status.HTTP_201_CREATED,
)
def create_memory(
    agent_id: str,
    memory_data: MemoryCreate,
):
    if not agent_exists(agent_id):
        raise HTTPException(
            status_code=404,
            detail="에이전트를 찾을 수 없습니다.",
        )

    new_memory = Memory(
        agent_id=agent_id,
        **memory_data.model_dump(),
    )

    memories.append(new_memory)

    # 새 기억을 JSON 파일에 저장
    save_memories(memories)

    return new_memory


@router.get(
    "/{agent_id}/memories",
    response_model=list[Memory],
)
def get_agent_memories(agent_id: str):
    if not agent_exists(agent_id):
        raise HTTPException(
            status_code=404,
            detail="에이전트를 찾을 수 없습니다.",
        )

    return [
        memory
        for memory in memories
        if memory.agent_id == agent_id
    ]


@router.get("/{agent_id}/memories/search")
def search_agent_memories(
    agent_id: str,
    query: str = Query(
        min_length=1,
        description="에이전트가 떠올릴 현재 상황 또는 주제",
    ),
    top_k: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
):
    if not agent_exists(agent_id):
        raise HTTPException(
            status_code=404,
            detail="에이전트를 찾을 수 없습니다.",
        )

    agent_memories = [
        memory
        for memory in memories
        if memory.agent_id == agent_id
    ]

    results = retrieve_memories(
        agent_memories=agent_memories,
        query=query,
        top_k=top_k,
    )

    accessed_at = datetime.now(timezone.utc)

    for result in results:
        result["memory"].last_accessed_at = accessed_at

    # 변경된 마지막 접근 시간을 JSON 파일에 저장
    save_memories(memories)

    return {
        "agent_id": agent_id,
        "query": query,
        "result_count": len(results),
        "results": results,
    }