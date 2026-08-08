from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .main import app


FRONTEND = Path(__file__).resolve().parents[1] / "web"


@app.get("/", include_in_schema=False)
def web_home() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

