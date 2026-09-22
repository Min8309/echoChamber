import random

from fastapi import APIRouter, HTTPException
from openai import OpenAIError

from app.models.conversation import ConversationRequest
from app.models.simulation import (
    AutonomousRunRequest,
    SimulationRunRequest,
    SimulationStepRequest,
)
from app.routers.agents import agents
from app.routers.conversations import (
    create_conversation,
)
from app.routers.memories import memories
from app.services.reflection import (
    generate_reflections,
)
from app.services.storage import save_memories
from app.services.planning import (
    generate_agent_plan,
)


router = APIRouter(
    prefix="/simulation",
    tags=["Simulation"],
)


@router.post("/step")
def run_simulation_step(
    request: SimulationStepRequest,
):
    if len(agents) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "시뮬레이션에는 최소 "
                "2명의 에이전트가 필요합니다."
            ),
        )

    speaker_weights = [
        max(
            0.01,
            (
                agent.personality.sociability
                * agent.personality.gossip_tendency
            ),
        )
        for agent in agents
    ]

    speaker = random.choices(
        agents,
        weights=speaker_weights,
        k=1,
    )[0]

    listener_candidates = [
        agent
        for agent in agents
        if agent.agent_id != speaker.agent_id
    ]

    listener_weights = [
        max(
            0.01,
            (
                agent.personality.sociability
                + agent.personality.credulity
            ),
        )
        for agent in listener_candidates
    ]

    listener = random.choices(
        listener_candidates,
        weights=listener_weights,
        k=1,
    )[0]

    conversation_request = ConversationRequest(
        speaker_id=speaker.agent_id,
        listener_id=listener.agent_id,
        topic=request.topic,
    )

    result = create_conversation(
        conversation_request
    )

    listener_memories = [
        memory
        for memory in memories
        if memory.agent_id == listener.agent_id
    ]

    try:
        reflection_result = generate_reflections(
            agent=listener,
            agent_memories=listener_memories,
            importance_threshold=20,
        )

    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"자동 반추 API 실패: {error}"
            ),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    new_reflections = reflection_result[
        "new_memories"
    ]

    if new_reflections:
        memories.extend(new_reflections)
        save_memories(memories)

    return {
        "selected_speaker": {
            "agent_id": speaker.agent_id,
            "name": speaker.name,
        },
        "selected_listener": {
            "agent_id": listener.agent_id,
            "name": listener.name,
        },
        "conversation": result,
        "reflection": {
            "triggered": reflection_result[
                "triggered"
            ],
            "reason": reflection_result[
                "reason"
            ],
            "importance_sum": (
                reflection_result[
                    "importance_sum"
                ]
            ),
            "new_memories": new_reflections,
        },
    }


@router.post("/run")
def run_simulation(
    request: SimulationRunRequest,
):
    results = []

    for step_number in range(
        1,
        request.steps + 1,
    ):
        step_request = SimulationStepRequest(
            topic=request.topic,
        )

        step_result = run_simulation_step(
            step_request
        )

        results.append(
            {
                "step": step_number,
                "selected_speaker": (
                    step_result[
                        "selected_speaker"
                    ]
                ),
                "selected_listener": (
                    step_result[
                        "selected_listener"
                    ]
                ),
                "conversation": (
                    step_result["conversation"]
                ),
                "reflection": (
                    step_result["reflection"]
                ),
            }
        )

    gossip_count = sum(
        1
        for result in results
        if result[
            "conversation"
        ]["analysis"].is_gossip
    )

    reflection_count = sum(
        1
        for result in results
        if result["reflection"]["triggered"]
    )

    return {
        "requested_steps": request.steps,
        "completed_steps": len(results),
        "gossip_count": gossip_count,
        "reflection_count": reflection_count,
        "results": results,
    }
@router.post("/autonomous-step")
def run_autonomous_simulation_step():
    if len(agents) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "자동 시뮬레이션에는 최소 "
                "2명의 에이전트가 필요합니다."
            ),
        )

    # 1. 발화자 선택
    speaker_weights = [
        max(
            0.01,
            (
                agent.personality.sociability
                * agent.personality.gossip_tendency
            ),
        )
        for agent in agents
    ]

    speaker = random.choices(
        agents,
        weights=speaker_weights,
        k=1,
    )[0]

    # 2. 발화자의 기억 불러오기
    speaker_memories = [
        memory
        for memory in memories
        if memory.agent_id == speaker.agent_id
    ]

    candidate_agents = [
        agent
        for agent in agents
        if agent.agent_id != speaker.agent_id
    ]

    # 3. Planning 실행
    try:
        planning_result = generate_agent_plan(
            agent=speaker,
            candidate_agents=candidate_agents,
            agent_memories=speaker_memories,
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

    plan = planning_result["plan"]
    plan_memory = planning_result["plan_memory"]

    # 4. 계획 메모리 저장
    memories.append(plan_memory)
    save_memories(memories)

    # 5. Planning이 선택한 상대 찾기
    listener = next(
        (
            agent
            for agent in agents
            if (
                agent.agent_id
                == plan.target_agent_id
            )
        ),
        None,
    )

    if listener is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Planning이 선택한 대상 "
                "에이전트를 찾을 수 없습니다."
            ),
        )

    # 6. Planning 주제로 실제 대화 실행
    conversation_request = ConversationRequest(
        speaker_id=speaker.agent_id,
        listener_id=listener.agent_id,
        topic=plan.topic,
    )

    conversation_result = create_conversation(
        conversation_request
    )

    # 7. 대화 후 청자의 기억으로 반추 실행
    listener_memories = [
        memory
        for memory in memories
        if memory.agent_id == listener.agent_id
    ]

    try:
        reflection_result = generate_reflections(
            agent=listener,
            agent_memories=listener_memories,
            importance_threshold=20,
        )

    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"자동 반추 API 실패: {error}"
            ),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    new_reflections = reflection_result[
        "new_memories"
    ]

    if new_reflections:
        memories.extend(new_reflections)
        save_memories(memories)

    return {
        "mode": "autonomous",
        "selected_speaker": {
            "agent_id": speaker.agent_id,
            "name": speaker.name,
        },
        "selected_listener": {
            "agent_id": listener.agent_id,
            "name": listener.name,
        },
        "planning": {
            "plan": plan,
            "retrieved_memory_ids": (
                planning_result[
                    "retrieved_memory_ids"
                ]
            ),
            "plan_memory_id": (
                plan_memory.memory_id
            ),
        },
        "conversation": conversation_result,
        "reflection": {
            "triggered": reflection_result[
                "triggered"
            ],
            "reason": reflection_result[
                "reason"
            ],
            "importance_sum": reflection_result[
                "importance_sum"
            ],
            "new_memories": new_reflections,
        },
    }
@router.post("/autonomous-run")
def run_autonomous_simulation(
    request: AutonomousRunRequest,
):
    results = []
    errors = []

    for step_number in range(
        1,
        request.steps + 1,
    ):
        try:
            step_result = (
                run_autonomous_simulation_step()
            )

            results.append(step_result)

        except HTTPException as error:
            errors.append(
                {
                    "step": step_number,
                    "status_code": (
                        error.status_code
                    ),
                    "detail": error.detail,
                }
            )

            # 서버 또는 OpenAI API 오류면
            # 남은 반복을 중단합니다.
            if error.status_code >= 500:
                break

        except Exception as error:
            errors.append(
                {
                    "step": step_number,
                    "status_code": 500,
                    "detail": str(error),
                }
            )

            break

    gossip_count = 0
    reflection_count = 0

    for result in results:
        conversation = result.get(
            "conversation",
            {},
        )

        analysis = conversation.get(
            "analysis"
        )

        if analysis is not None:
            if hasattr(
                analysis,
                "is_gossip",
            ):
                is_gossip = (
                    analysis.is_gossip
                )
            else:
                is_gossip = analysis.get(
                    "is_gossip",
                    False,
                )

            if is_gossip:
                gossip_count += 1

        reflection = result.get(
            "reflection",
            {},
        )

        if reflection.get(
            "triggered",
            False,
        ):
            reflection_count += 1

    return {
        "mode": "autonomous-run",
        "requested_steps": request.steps,
        "completed_steps": len(results),
        "failed_steps": len(errors),
        "gossip_count": gossip_count,
        "reflection_count": reflection_count,
        "results": results,
        "errors": errors,
    }