import json
from pathlib import Path

from app.models.agent import Agent
from app.models.gossip import GossipEvent
from app.models.memory import Memory
from app.models.message import RealMessage


DATA_DIRECTORY = Path("data")

AGENTS_FILE = DATA_DIRECTORY / "agents.json"
MEMORIES_FILE = DATA_DIRECTORY / "memories.json"
GOSSIP_EVENTS_FILE = DATA_DIRECTORY / "gossip_events.json"
MESSAGES_FILE = DATA_DIRECTORY / "messages.json"


def prepare_data_directory():
    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_agents() -> list[Agent]:
    prepare_data_directory()

    if not AGENTS_FILE.exists():
        return []

    with AGENTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    return [
        Agent.model_validate(item)
        for item in raw_data
    ]


def save_agents(agents: list[Agent]):
    prepare_data_directory()

    data = [
        agent.model_dump(mode="json")
        for agent in agents
    ]

    with AGENTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_memories() -> list[Memory]:
    prepare_data_directory()

    if not MEMORIES_FILE.exists():
        return []

    with MEMORIES_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    return [
        Memory.model_validate(item)
        for item in raw_data
    ]


def save_memories(memories: list[Memory]):
    prepare_data_directory()

    data = [
        memory.model_dump(mode="json")
        for memory in memories
    ]

    with MEMORIES_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_gossip_events() -> list[GossipEvent]:
    prepare_data_directory()

    if not GOSSIP_EVENTS_FILE.exists():
        return []

    with GOSSIP_EVENTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    return [
        GossipEvent.model_validate(item)
        for item in raw_data
    ]


def save_gossip_events(
    gossip_events: list[GossipEvent],
):
    prepare_data_directory()

    data = [
        event.model_dump(mode="json")
        for event in gossip_events
    ]

    with GOSSIP_EVENTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
def load_messages() -> list[RealMessage]:
    prepare_data_directory()

    if not MESSAGES_FILE.exists():
        return []

    with MESSAGES_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    return [
        RealMessage.model_validate(item)
        for item in raw_data
    ]


def save_messages(messages: list[RealMessage]):
    prepare_data_directory()

    data = [
        message.model_dump(mode="json")
        for message in messages
    ]

    with MESSAGES_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )