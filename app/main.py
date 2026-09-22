from fastapi import FastAPI

from app.routers.reflections import router as reflections_router
from app.routers.agents import router as agents_router
from app.routers.memories import router as memories_router
from app.routers.conversations import router as conversations_router
from app.routers.network import router as network_router
from app.routers.analysis import router as analysis_router
from app.routers.simulation import router as simulation_router
from app.routers.planning import (
    router as planning_router,
)
from app.routers.ingestion import (
    router as ingestion_router,
)


app = FastAPI(
    title="EchoChamber API",
    description="가십 역학 시뮬레이션 및 분석 플랫폼",
    version="0.1.0",
)


app.include_router(agents_router)
app.include_router(memories_router)
app.include_router(conversations_router)
app.include_router(network_router)
app.include_router(analysis_router)
app.include_router(simulation_router)
app.include_router(reflections_router)
app.include_router(planning_router)
app.include_router(ingestion_router)

@app.get("/")
def read_root():
    return {
        "project": "EchoChamber",
        "status": "running",
        "message": "EchoChamber API 서버가 정상적으로 실행 중입니다.",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }

