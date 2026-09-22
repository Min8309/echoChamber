from fastapi import APIRouter, HTTPException, status
from openai import OpenAIError

from app.models.conversation import (
    ConversationRequest,
    ConversationResponse,
)
from app.models.gossip import GossipEvent
from app.routers.agents import agents
from app.routers.memories import memories
from app.services.analysis import analyze_dialogue
from app.services.conversation import generate_conversation
from app.services.storage import (
    load_gossip_events,
    save_gossip_events,
    save_memories,
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


gossip_events: list[GossipEvent] = load_gossip_events()


def find_agent(agent_id: str):
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent

    return None


@router.get(
    "/gossip-events",
    response_model=list[GossipEvent],
)
def get_gossip_events():
    return gossip_events


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: ConversationRequest,
):
    speaker = find_agent(request.speaker_id)
    listener = find_agent(request.listener_id)

    if speaker is None:
        raise HTTPException(
            status_code=404,
            detail="말하는 에이전트를 찾을 수 없습니다.",
        )

    if listener is None:
        raise HTTPException(
            status_code=404,
            detail="듣는 에이전트를 찾을 수 없습니다.",
        )

    if speaker.agent_id == listener.agent_id:
        raise HTTPException(
            status_code=400,
            detail="같은 에이전트끼리는 대화할 수 없습니다.",
        )

    speaker_memories = [
        memory
        for memory in memories
        if memory.agent_id == speaker.agent_id
    ]

    try:
        result = generate_conversation(
            speaker=speaker,
            listener=listener,
            topic=request.topic,
            speaker_memories=speaker_memories,
        )

        analysis = analyze_dialogue(
            text=result["utterance"],
            speaker_name=speaker.name,
            listener_name=listener.name,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI API 요청 실패: {error}",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    result["analysis"] = analysis

    memories.append(result["listener_memory"])
    save_memories(memories)

    if analysis.is_gossip:
        gossip_event = GossipEvent(
            speaker_id=speaker.agent_id,
            listener_id=listener.agent_id,
            topic=request.topic,
            utterance=result["utterance"],
            analysis=analysis,
        )

        gossip_events.append(gossip_event)
        save_gossip_events(gossip_events)

    return result