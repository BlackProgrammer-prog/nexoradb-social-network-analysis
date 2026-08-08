from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import main as api_module
from .ready_service import ReadyNexoraSocialService
from .settings import settings


FRONTEND = Path(__file__).resolve().parents[1] / "web"


@lru_cache(maxsize=1)
def ready_service() -> ReadyNexoraSocialService:
    return ReadyNexoraSocialService(settings)


# Existing route functions resolve this module global at request time, so the
# external API keeps the same endpoints while using the readiness-aware service.
api_module.service = ready_service
app = api_module.app


@app.get("/", include_in_schema=False)
def web_home_v2() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

