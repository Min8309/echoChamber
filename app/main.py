import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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

# stitch UI 정적 폴더 서빙 (있을 경우)
stitch_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stitch")
if os.path.exists(stitch_dir):
    app.mount("/stitch", StaticFiles(directory=stitch_dir), name="stitch")


@app.get("/", response_class=HTMLResponse)
def read_root():
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stitch", "code.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>EchoChamber API 서버가 실행 중입니다.</h1>
            <p>UI 파일(stitch/code.html)을 찾을 수 없습니다.</p>
        </body>
    </html>
    """


@app.get("/real-lab", response_class=HTMLResponse)
def read_real_lab():
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stitch", "code_01.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>EchoChamber - 현실 댓글 연구실</h1>
            <p>UI 파일(stitch/code_01.html)을 찾을 수 없습니다.</p>
        </body>
    </html>
    """


@app.get("/education", response_class=HTMLResponse)
def read_education():
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stitch", "code_02.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>EchoChamber Learning Lab</h1>
            <p>UI 파일(stitch/code_02.html)을 찾을 수 없습니다.</p>
        </body>
    </html>
    """


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


