import os
import asyncio
from contextlib import asynccontextmanager, suppress
from starlette.concurrency import run_in_threadpool
from app.services import datasets as research_datasets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.limits import enabled
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers.workbench import router as workbench_router
from app.routers.datasets import router as datasets_router
from app.routers.collection import router as collection_router

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


def cleanup_research():
    research_datasets.connect().close()


@asynccontextmanager
async def research_lifespan(app):
    await run_in_threadpool(cleanup_research)

    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)
            await run_in_threadpool(cleanup_research)

    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=research_lifespan,
    docs_url=None if enabled("DISABLE_DOCS") else "/docs",
    redoc_url=None if enabled("DISABLE_DOCS") else "/redoc",
    openapi_url=None if enabled("DISABLE_DOCS") else "/openapi.json",
    title="EchoChamber API",
    description="가십 역학 시뮬레이션 및 분석 플랫폼",
    version="0.1.0",
)


cors_origins = [
    value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Dataset-Key"],
        expose_headers=["Retry-After"],
    )


app.include_router(workbench_router)
app.include_router(datasets_router)
app.include_router(collection_router)
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
    react_index = (
        Path(__file__).resolve().parents[1] / "frontend" / "dist" / "index.html"
    )
    if react_index.is_file():
        return FileResponse(react_index)
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "stitch", "code.html"
    )
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
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "stitch", "code_01.html"
    )
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
    """학습 연구실 UI 페이지를 반환합니다."""
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "stitch", "code_02.html"
    )
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


@app.get("/alexandria", response_class=HTMLResponse)
def read_alexandria():
    """알렉산드리아 UI 페이지를 반환합니다."""
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "stitch", "alexandria", "code.html"
    )
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>EchoChamber Alexandria</h1>
            <p>UI 파일(stitch/alexandria/code.html)을 찾을 수 없습니다.</p>
        </body>
    </html>
    """


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Vite builds assets with an absolute /assets/ base for same-origin API hosting.
react_assets = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets"
if react_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=react_assets), name="react-assets")

# Reviewed project deck and downloadable PowerPoint files; no private research data.
presentation_dir = Path(__file__).resolve().parents[1] / "docs" / "presentation"
if presentation_dir.is_dir():
    app.mount(
        "/presentation",
        StaticFiles(directory=presentation_dir, html=True),
        name="project-presentation",
    )
