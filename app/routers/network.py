import re
from difflib import SequenceMatcher

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from app.models.memory import MemoryType
from app.routers.agents import agents
from app.routers.memories import memories
from app.services.storage import load_gossip_events


def normalize_rumor_text(
    text: str,
) -> str:
    normalized = text.lower().strip()

    # "Isabella가 말했다:" 같은
    # 대화 기억 접두사를 제거합니다.
    normalized = re.sub(
        r"^.+?가 말했다:\s*",
        "",
        normalized,
        count=1,
    )

    normalized = re.sub(
        r"[^0-9a-zA-Z가-힣\s]",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def calculate_text_similarity(
    first_text: str,
    second_text: str,
) -> float:
    first_normalized = normalize_rumor_text(
        first_text
    )

    second_normalized = normalize_rumor_text(
        second_text
    )

    if (
        not first_normalized
        and not second_normalized
    ):
        return 1.0

    if (
        not first_normalized
        or not second_normalized
    ):
        return 0.0

    sequence_similarity = SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio()

    first_tokens = set(
        first_normalized.split()
    )

    second_tokens = set(
        second_normalized.split()
    )

    token_union = (
        first_tokens
        | second_tokens
    )

    if token_union:
        token_similarity = len(
            first_tokens
            & second_tokens
        ) / len(token_union)
    else:
        token_similarity = 0.0

    # 문장 구조 유사도와 단어 유사도를 결합합니다.
    combined_similarity = (
        sequence_similarity * 0.6
        + token_similarity * 0.4
    )

    return round(
        combined_similarity,
        4,
    )


router = APIRouter(
    prefix="/network",
    tags=["Network"],
)


def get_reputation_statistics(gossip_events):
    reputation_scores = {
        agent.agent_id: 0.0
        for agent in agents
    }

    mentioned_counts = {
        agent.agent_id: 0
        for agent in agents
    }

    sent_gossip_counts = {
        agent.agent_id: 0
        for agent in agents
    }

    received_gossip_counts = {
        agent.agent_id: 0
        for agent in agents
    }

    unresolved_subjects = []

    for event in gossip_events:
        sent_gossip_counts[event.speaker_id] = (
            sent_gossip_counts.get(
                event.speaker_id,
                0,
            )
            + 1
        )

        received_gossip_counts[event.listener_id] = (
            received_gossip_counts.get(
                event.listener_id,
                0,
            )
            + 1
        )

        subject = event.analysis.subject

        if subject is None:
            continue

        matching_agents = [
            agent
            for agent in agents
            if agent.name.casefold()
            == subject.casefold()
        ]

        if len(matching_agents) != 1:
            unresolved_subjects.append(subject)
            continue

        subject_agent = matching_agents[0]

        reputation_scores[subject_agent.agent_id] += (
            event.analysis.reputation_impact
        )

        mentioned_counts[subject_agent.agent_id] += 1

    return {
        "reputation_scores": reputation_scores,
        "mentioned_counts": mentioned_counts,
        "sent_gossip_counts": sent_gossip_counts,
        "received_gossip_counts": (
            received_gossip_counts
        ),
        "unresolved_subjects": list(
            dict.fromkeys(unresolved_subjects)
        ),
    }


def find_matching_gossip_event(
    memory,
    gossip_events,
):
    for event in reversed(gossip_events):
        same_sender = (
            event.speaker_id
            == memory.source_agent_id
        )

        same_receiver = (
            event.listener_id
            == memory.agent_id
        )

        utterance_in_memory = (
            event.utterance
            in memory.description
        )

        if (
            same_sender
            and same_receiver
            and utterance_in_memory
        ):
            return event

    return None


@router.get("")
def get_network():
    gossip_events = load_gossip_events()

    statistics = get_reputation_statistics(
        gossip_events
    )

    nodes = []

    for agent in agents:
        nodes.append(
            {
                "id": agent.agent_id,
                "label": agent.name,
                "age": agent.age,
                "occupation": agent.occupation,
                "location": agent.current_location,
                "goal": agent.current_goal,
                "sociability": (
                    agent.personality.sociability
                ),
                "gossip_tendency": (
                    agent.personality.gossip_tendency
                ),
                "credulity": (
                    agent.personality.credulity
                ),
                "reputation_score": (
                    statistics[
                        "reputation_scores"
                    ].get(
                        agent.agent_id,
                        0.0,
                    )
                ),
                "mentioned_count": (
                    statistics[
                        "mentioned_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
                "sent_gossip_count": (
                    statistics[
                        "sent_gossip_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
                "received_gossip_count": (
                    statistics[
                        "received_gossip_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
            }
        )

    edges = []

    for memory in memories:
        if (
            memory.memory_type
            != MemoryType.dialogue
        ):
            continue

        if memory.source_agent_id is None:
            continue

        gossip_event = find_matching_gossip_event(
            memory=memory,
            gossip_events=gossip_events,
        )

        edge = {
            "id": memory.memory_id,
            "source": memory.source_agent_id,
            "target": memory.agent_id,
            "label": "정보 전달",
            "description": memory.description,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "created_at": memory.created_at,
            "evidence_memory_ids": (
                memory.evidence_memory_ids
            ),
            "is_gossip": gossip_event is not None,
            "subject": None,
            "sentiment": None,
            "certainty": None,
            "reputation_impact": 0.0,
        }

        if gossip_event is not None:
            edge["label"] = "가십 전달"
            edge["subject"] = (
                gossip_event.analysis.subject
            )
            edge["sentiment"] = (
                gossip_event.analysis.sentiment.value
            )
            edge["certainty"] = (
                gossip_event.analysis.certainty.value
            )
            edge["reputation_impact"] = (
                gossip_event.analysis.reputation_impact
            )

        edges.append(edge)

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "gossip_event_count": len(
            gossip_events
        ),
        "unresolved_subjects": statistics[
            "unresolved_subjects"
        ],
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/summary")
def get_network_summary():
    gossip_events = load_gossip_events()

    statistics = get_reputation_statistics(
        gossip_events
    )

    dialogue_memories = [
        memory
        for memory in memories
        if (
            memory.memory_type
            == MemoryType.dialogue
            and memory.source_agent_id is not None
        )
    ]

    received_counts: dict[str, int] = {}
    shared_counts: dict[str, int] = {}

    for memory in dialogue_memories:
        receiver_id = memory.agent_id
        sender_id = memory.source_agent_id

        received_counts[receiver_id] = (
            received_counts.get(
                receiver_id,
                0,
            )
            + 1
        )

        shared_counts[sender_id] = (
            shared_counts.get(
                sender_id,
                0,
            )
            + 1
        )

    agent_names = {
        agent.agent_id: agent.name
        for agent in agents
    }

    agent_statistics = []

    for agent in agents:
        agent_statistics.append(
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "shared_count": (
                    shared_counts.get(
                        agent.agent_id,
                        0,
                    )
                ),
                "received_count": (
                    received_counts.get(
                        agent.agent_id,
                        0,
                    )
                ),
                "sent_gossip_count": (
                    statistics[
                        "sent_gossip_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
                "received_gossip_count": (
                    statistics[
                        "received_gossip_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
                "mentioned_count": (
                    statistics[
                        "mentioned_counts"
                    ].get(
                        agent.agent_id,
                        0,
                    )
                ),
                "reputation_score": (
                    statistics[
                        "reputation_scores"
                    ].get(
                        agent.agent_id,
                        0.0,
                    )
                ),
            }
        )

    most_active_sender = None

    if shared_counts:
        sender_id = max(
            shared_counts,
            key=shared_counts.get,
        )

        most_active_sender = {
            "agent_id": sender_id,
            "name": agent_names.get(
                sender_id,
                "Unknown",
            ),
            "shared_count": (
                shared_counts[sender_id]
            ),
        }

    return {
        "total_agents": len(agents),
        "total_transmissions": len(
            dialogue_memories
        ),
        "total_gossip_events": len(
            gossip_events
        ),
        "most_active_sender": (
            most_active_sender
        ),
        "unresolved_subjects": statistics[
            "unresolved_subjects"
        ],
        "agent_statistics": agent_statistics,
    }
@router.get("/cascades")
def get_rumor_cascades(
    min_transmissions: int = Query(
        default=1,
        ge=1,
        description="최소 정보 전달 횟수",
    ),
):
    memory_by_id = {
        memory.memory_id: memory
        for memory in memories
    }

    agent_names = {
        agent.agent_id: agent.name
        for agent in agents
    }

    root_cache: dict[
        str,
        set[str],
    ] = {}

    depth_cache: dict[str, int] = {}

    def find_root_memory_ids(
        memory_id: str,
        visiting: set[str] | None = None,
    ) -> set[str]:
        if memory_id in root_cache:
            return root_cache[memory_id]

        if visiting is None:
            visiting = set()

        # 잘못된 순환 참조 방지
        if memory_id in visiting:
            return {memory_id}

        memory = memory_by_id.get(memory_id)

        if memory is None:
            return set()

        next_visiting = visiting | {memory_id}

        evidence_ids = [
            evidence_id
            for evidence_id
            in memory.evidence_memory_ids
            if evidence_id in memory_by_id
        ]

        if not evidence_ids:
            roots = {memory_id}

        else:
            roots = set()

            for evidence_id in evidence_ids:
                roots.update(
                    find_root_memory_ids(
                        evidence_id,
                        next_visiting,
                    )
                )

            if not roots:
                roots = {memory_id}

        root_cache[memory_id] = roots

        return roots

    def calculate_depth(
        memory_id: str,
        visiting: set[str] | None = None,
    ) -> int:
        if memory_id in depth_cache:
            return depth_cache[memory_id]

        if visiting is None:
            visiting = set()

        if memory_id in visiting:
            return 0

        memory = memory_by_id.get(memory_id)

        if memory is None:
            return 0

        evidence_ids = [
            evidence_id
            for evidence_id
            in memory.evidence_memory_ids
            if evidence_id in memory_by_id
        ]

        if not evidence_ids:
            depth = 0

        else:
            next_visiting = visiting | {
                memory_id
            }

            depth = 1 + max(
                calculate_depth(
                    evidence_id,
                    next_visiting,
                )
                for evidence_id in evidence_ids
            )

        depth_cache[memory_id] = depth

        return depth

    cascades: dict[str, dict] = {}

    dialogue_memories = [
        memory
        for memory in memories
        if (
            memory.memory_type
            == MemoryType.dialogue
            and memory.source_agent_id
            is not None
        )
    ]

    for dialogue_memory in dialogue_memories:
        root_ids = find_root_memory_ids(
            dialogue_memory.memory_id
        )

        for root_id in root_ids:
            root_memory = memory_by_id.get(
                root_id
            )

            if root_memory is None:
                continue

            if root_id not in cascades:
                cascades[root_id] = {
                    "root_memory": root_memory,
                    "transmissions": [],
                    "participant_ids": set(),
                    "subject_agent_ids": set(),
                }

            cascade = cascades[root_id]

            source_id = (
                dialogue_memory.source_agent_id
            )

            target_id = dialogue_memory.agent_id

            cascade["participant_ids"].add(
                source_id
            )

            cascade["participant_ids"].add(
                target_id
            )

            cascade[
                "subject_agent_ids"
            ].update(
                dialogue_memory.subject_agent_ids
            )

            cascade["transmissions"].append(
                {
                    "memory_id": (
                        dialogue_memory.memory_id
                    ),
                    "source": {
                        "agent_id": source_id,
                        "name": agent_names.get(
                            source_id,
                            "Unknown",
                        ),
                    },
                    "target": {
                        "agent_id": target_id,
                        "name": agent_names.get(
                            target_id,
                            "Unknown",
                        ),
                    },
                    "description": (
                        dialogue_memory.description
                    ),
                    "importance": (
                        dialogue_memory.importance
                    ),
                    "confidence": (
                        dialogue_memory.confidence
                    ),
                    "depth": calculate_depth(
                        dialogue_memory.memory_id
                    ),
                    "created_at": (
                        dialogue_memory.created_at
                    ),
                    "evidence_memory_ids": (
                        dialogue_memory
                        .evidence_memory_ids
                    ),
                }
            )

    results = []

    for root_id, cascade in cascades.items():
        transmissions = cascade[
            "transmissions"
        ]

        if (
            len(transmissions)
            < min_transmissions
        ):
            continue

        transmissions.sort(
            key=lambda item: item["created_at"]
        )

        root_memory = cascade[
            "root_memory"
        ]

        average_confidence = sum(
            item["confidence"]
            for item in transmissions
        ) / len(transmissions)

        maximum_depth = max(
            item["depth"]
            for item in transmissions
        )

        participant_ids = sorted(
            cascade["participant_ids"]
        )

        subject_agent_ids = sorted(
            cascade["subject_agent_ids"]
        )

        results.append(
            {
                "cascade_id": root_id,
                "root_memory": {
                    "memory_id": (
                        root_memory.memory_id
                    ),
                    "memory_type": (
                        root_memory
                        .memory_type
                        .value
                    ),
                    "agent_id": (
                        root_memory.agent_id
                    ),
                    "agent_name": (
                        agent_names.get(
                            root_memory.agent_id,
                            "Unknown",
                        )
                    ),
                    "description": (
                        root_memory.description
                    ),
                    "importance": (
                        root_memory.importance
                    ),
                    "confidence": (
                        root_memory.confidence
                    ),
                    "created_at": (
                        root_memory.created_at
                    ),
                },
                "transmission_count": len(
                    transmissions
                ),
                "participant_count": len(
                    participant_ids
                ),
                "max_depth": maximum_depth,
                "average_confidence": round(
                    average_confidence,
                    3,
                ),
                "started_at": (
                    root_memory.created_at
                ),
                "last_transmission_at": (
                    transmissions[-1][
                        "created_at"
                    ]
                ),
                "participants": [
                    {
                        "agent_id": agent_id,
                        "name": agent_names.get(
                            agent_id,
                            "Unknown",
                        ),
                    }
                    for agent_id
                    in participant_ids
                ],
                "subjects": [
                    {
                        "agent_id": agent_id,
                        "name": agent_names.get(
                            agent_id,
                            "Unknown",
                        ),
                    }
                    for agent_id
                    in subject_agent_ids
                ],
                "transmissions": transmissions,
            }
        )

    results.sort(
        key=lambda item: (
            item["transmission_count"],
            item["max_depth"],
        ),
        reverse=True,
    )

    largest_cascade = None

    if results:
        largest = results[0]

        largest_cascade = {
            "cascade_id": largest[
                "cascade_id"
            ],
            "description": largest[
                "root_memory"
            ]["description"],
            "transmission_count": largest[
                "transmission_count"
            ],
            "participant_count": largest[
                "participant_count"
            ],
            "max_depth": largest[
                "max_depth"
            ],
        }

    return {
        "cascade_count": len(results),
        "dialogue_memory_count": len(
            dialogue_memories
        ),
        "largest_cascade": largest_cascade,
        "cascades": results,
    }
@router.get(
    "/cascades/{cascade_id}/distortion"
)
def get_cascade_distortion(
    cascade_id: str,
):
    cascade_response = get_rumor_cascades(
        min_transmissions=1
    )

    selected_cascade = next(
        (
            cascade
            for cascade
            in cascade_response["cascades"]
            if (
                cascade["cascade_id"]
                == cascade_id
            )
        ),
        None,
    )

    if selected_cascade is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "해당 소문 전파 경로를 "
                "찾을 수 없습니다."
            ),
        )

    memory_by_id = {
        memory.memory_id: memory
        for memory in memories
    }

    root_memory = selected_cascade[
        "root_memory"
    ]

    root_description = root_memory[
        "description"
    ]

    root_confidence = float(
        root_memory.get(
            "confidence",
            1.0,
        )
    )

    analysis_steps = []

    transmissions = selected_cascade.get(
        "transmissions",
        [],
    )

    for order, transmission in enumerate(
        transmissions,
        start=1,
    ):
        memory_id = transmission[
            "memory_id"
        ]

        current_memory = memory_by_id.get(
            memory_id
        )

        current_description = transmission[
            "description"
        ]

        current_confidence = float(
            transmission.get(
                "confidence",
                0.0,
            )
        )

        parent_memory = None

        if current_memory is not None:
            for evidence_id in (
                current_memory
                .evidence_memory_ids
            ):
                evidence_memory = (
                    memory_by_id.get(
                        evidence_id
                    )
                )

                if evidence_memory is not None:
                    parent_memory = (
                        evidence_memory
                    )
                    break

        if parent_memory is None:
            parent_description = (
                root_description
            )

            parent_confidence = (
                root_confidence
            )

            parent_memory_id = (
                root_memory["memory_id"]
            )

        else:
            parent_description = (
                parent_memory.description
            )

            parent_confidence = float(
                parent_memory.confidence
            )

            parent_memory_id = (
                parent_memory.memory_id
            )

        similarity_from_root = (
            calculate_text_similarity(
                root_description,
                current_description,
            )
        )

        similarity_from_parent = (
            calculate_text_similarity(
                parent_description,
                current_description,
            )
        )

        distortion_from_root = round(
            1.0 - similarity_from_root,
            4,
        )

        distortion_from_parent = round(
            1.0 - similarity_from_parent,
            4,
        )

        confidence_loss_from_root = round(
            root_confidence
            - current_confidence,
            4,
        )

        hop_confidence_loss = round(
            parent_confidence
            - current_confidence,
            4,
        )

        analysis_steps.append(
            {
                "order": order,
                "memory_id": memory_id,
                "parent_memory_id": (
                    parent_memory_id
                ),
                "depth": transmission.get(
                    "depth",
                    0,
                ),
                "source": transmission[
                    "source"
                ],
                "target": transmission[
                    "target"
                ],
                "description": (
                    current_description
                ),
                "similarity_from_root": (
                    similarity_from_root
                ),
                "distortion_from_root": (
                    distortion_from_root
                ),
                "similarity_from_parent": (
                    similarity_from_parent
                ),
                "distortion_from_parent": (
                    distortion_from_parent
                ),
                "confidence": (
                    current_confidence
                ),
                "confidence_loss_from_root": (
                    confidence_loss_from_root
                ),
                "hop_confidence_loss": (
                    hop_confidence_loss
                ),
                "created_at": transmission[
                    "created_at"
                ],
            }
        )

    if analysis_steps:
        average_distortion = sum(
            step["distortion_from_root"]
            for step in analysis_steps
        ) / len(analysis_steps)

        maximum_distortion_step = max(
            analysis_steps,
            key=lambda step: (
                step[
                    "distortion_from_root"
                ]
            ),
        )

        final_step = analysis_steps[-1]

        average_confidence = sum(
            step["confidence"]
            for step in analysis_steps
        ) / len(analysis_steps)

        summary = {
            "average_distortion": round(
                average_distortion,
                4,
            ),
            "maximum_distortion": (
                maximum_distortion_step[
                    "distortion_from_root"
                ]
            ),
            "most_distorted_order": (
                maximum_distortion_step[
                    "order"
                ]
            ),
            "final_distortion": (
                final_step[
                    "distortion_from_root"
                ]
            ),
            "root_confidence": (
                root_confidence
            ),
            "final_confidence": (
                final_step["confidence"]
            ),
            "total_confidence_loss": round(
                root_confidence
                - final_step["confidence"],
                4,
            ),
            "average_confidence": round(
                average_confidence,
                4,
            ),
        }

    else:
        summary = {
            "average_distortion": 0.0,
            "maximum_distortion": 0.0,
            "most_distorted_order": None,
            "final_distortion": 0.0,
            "root_confidence": (
                root_confidence
            ),
            "final_confidence": (
                root_confidence
            ),
            "total_confidence_loss": 0.0,
            "average_confidence": (
                root_confidence
            ),
        }

    return {
        "cascade_id": cascade_id,
        "root_memory": root_memory,
        "transmission_count": len(
            analysis_steps
        ),
        "summary": summary,
        "steps": analysis_steps,
    }