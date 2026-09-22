from pydantic import BaseModel, Field
from pydantic import BaseModel, Field


class SimulationStepRequest(BaseModel):
    topic: str = Field(
        min_length=1,
        description="이번 시뮬레이션의 대화 주제",
    )


class SimulationRunRequest(BaseModel):
    topic: str = Field(
        min_length=1,
        description="연속 시뮬레이션의 대화 주제",
    )

    steps: int = Field(
        default=3,
        ge=1,
        le=5,
        description="실행할 대화 단계 수",
    )
class AutonomousRunRequest(BaseModel):
    steps: int = Field(
        default=3,
        ge=1,
        le=20,
        description="자동 시뮬레이션 반복 횟수",
    )    