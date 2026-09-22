from uuid import uuid4

from pydantic import BaseModel, Field


class Personality(BaseModel):
    sociability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="사교성",
    )
    gossip_tendency: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="소문 전달 성향",
    )
    credulity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="소문을 쉽게 믿는 정도",
    )


class Agent(BaseModel):
    agent_id: str = Field(
        default_factory=lambda: str(uuid4())
    )
    name: str
    age: int = Field(ge=1, le=120)
    occupation: str
    current_location: str
    current_goal: str
    personality: Personality