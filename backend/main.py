from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import MODEL

from app.routes import (
    auth,
    health,
    chat,
    project,
    agent,
)


app = FastAPI(
    title="Local Coding AI"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    auth.router,
    prefix="/api"
)

app.include_router(
    health.router,
    prefix="/api"
)

app.include_router(
    chat.router,
    prefix="/api"
)

app.include_router(
    project.router,
    prefix="/api"
)

app.include_router(
    agent.router,
    prefix="/api"
)


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")


@app.get("/")
async def root():
    frontend_root = Path(__file__).resolve().parent.parent / "frontend"
    frontend = frontend_root / "dist" / "index.html"
    if not frontend.is_file():
        frontend = frontend_root / "index.html"
    return FileResponse(frontend)