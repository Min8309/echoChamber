from enum import Enum

from pydantic import BaseModel, Field


class PlanAction(str, Enum):
    share_information = "share_information"
    ask_question = "ask_question"
    verify_rumor = "verify_rumor"
    build_relationship = "build_relationship"
    invite = "invite"


class AgentPlan(BaseModel):
    action: PlanAction = Field(
        description="계획한 대화 행동"
    )

    target_agent_id: str = Field(
        description="대화 대상 에이전트 ID"
    )

    topic: str = Field(
        min_length=1,
        description="다음 대화에서 사용할 주제",
    )

    reason: str = Field(
        min_length=1,
        description="이 계획을 선택한 이유",
    )

    priority: int = Field(
        ge=1,
        le=10,
        description="계획의 우선순위",
    )