from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .file_parser import FileFormatError, parse_relationship_file
from .nexora_service import DRIVER_ERRORS, NexoraSocialService, ServiceError
from .schemas import AlgorithmRequest, RelationshipCreate, UserCreate, UserUpdate
from .settings import settings


app = FastAPI(
    title="Social Network Analysis API",
    description="External demo API connected to NexoraDB through its Python driver.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def service() -> NexoraSocialService:
    return NexoraSocialService(settings)


def fail(exc: Exception) -> None:
    if isinstance(exc, ServiceError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if isinstance(exc, DRIVER_ERRORS):
        raise HTTPException(status_code=503, detail=f"خطا در اتصال به NexoraDB: {exc}") from exc
    raise exc


@app.get("/api/v1/health")
def health() -> dict:
    try:
        connected = service().ping()
        return {"status": "ok" if connected else "degraded", "database_connected": connected}
    except Exception as exc:
        return {"status": "degraded", "database_connected": False, "message": str(exc)}


@app.post("/api/v1/setup")
def setup() -> dict:
    try:
        service().ensure_schema()
        return {"message": "collectionها و LiveGraph آماده هستند.", "build_required": False}
    except Exception as exc:
        fail(exc)


@app.get("/api/v1/dashboard")
def dashboard() -> dict:
    try:
        return service().dashboard()
    except Exception as exc:
        fail(exc)


@app.post("/api/v1/imports/relationships")
async def import_relationships(file: UploadFile = File(...)) -> dict:
    if file.size is not None and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="حداکثر اندازه فایل ۱۰ مگابایت است.")
    content = await file.read()
    try:
        parsed = parse_relationship_file(content)
        return service().import_parsed(parsed)
    except FileFormatError as exc:
        raise HTTPException(status_code=400, detail={"message": "فایل نامعتبر است.", "errors": exc.errors}) from exc
    except Exception as exc:
        fail(exc)


@app.get("/api/v1/users")
def list_users(search: str = "", limit: int = Query(default=1000, ge=1, le=10000)) -> dict:
    try:
        items = service().list_users(limit=limit)
        if search.strip():
            needle = search.strip().lower()
            items = [
                item for item in items
                if needle in str(item.get("_id", "")).lower()
                or needle in str(item.get("username", "")).lower()
            ]
        return {"items": items, "total": len(items)}
    except Exception as exc:
        fail(exc)


@app.post("/api/v1/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    try:
        return service().create_user(payload.id, payload.username)
    except Exception as exc:
        fail(exc)


@app.put("/api/v1/users/{user_id}")
def update_user(user_id: str, payload: UserUpdate) -> dict:
    try:
        return service().update_user(user_id, payload.username)
    except Exception as exc:
        fail(exc)


@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: str) -> dict:
    try:
        return service().delete_user(user_id)
    except Exception as exc:
        fail(exc)


@app.get("/api/v1/relationships")
def list_relationships() -> dict:
    try:
        items = service().list_relationships()
        return {"items": items, "total": len(items)}
    except Exception as exc:
        fail(exc)


@app.post("/api/v1/relationships", status_code=201)
def create_relationship(payload: RelationshipCreate) -> dict:
    try:
        return service().create_relationship(payload.user_a, payload.user_b)
    except Exception as exc:
        fail(exc)


@app.delete("/api/v1/relationships/{user_a}/{user_b}")
def delete_relationship(user_a: str, user_b: str) -> dict:
    try:
        return service().delete_relationship(user_a, user_b)
    except Exception as exc:
        fail(exc)


@app.get("/api/v1/graph")
def graph() -> dict:
    try:
        return service().graph_view()
    except Exception as exc:
        fail(exc)


@app.post("/api/v1/algorithms/{name}")
def run_algorithm(name: str, payload: AlgorithmRequest) -> dict:
    try:
        return service().run_algorithm(name, payload.parameters)
    except Exception as exc:
        fail(exc)

