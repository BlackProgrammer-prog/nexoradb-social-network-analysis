"""FastAPI application for the NexoraDB Social Graph Service.

This is the main entry point for the backend service. All endpoints
are defined here with proper authentication and error handling.
"""

from __future__ import annotations

import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware

from settings import settings
from nexora_client import create_nexora_client, NexoraDBConnectionError, NexoraDBQueryError
from schemas import (
    HealthResponse, ImportResponse, UserCreate, UserUpdate,
    RelationshipCreate, GraphSnapshot, AlgorithmRequest, AlgorithmResponse,
    ErrorResponse
)
from import_service import process_import, generate_insert_queries
from repositories import UserRepository, RelationshipRepository, GraphRepository
from algorithm_service import AlgorithmService, ALL_ALGORITHMS, LOCK_ALGORITHMS, JOB_ALGORITHMS

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")

    # Validate critical settings
    settings.validate_for_startup()

    # Initialize client and check connectivity
    client = create_nexora_client(settings)
    if not client.ping():
        logger.warning("NexoraDB is not reachable! Please check the connection.")
    else:
        logger.info("Connected to NexoraDB successfully ✅")

    # Store client in app state
    app.state.client = client

    # Ensure collections and graph exist (idempotent)
    _ensure_initial_setup(client)

    yield

    logger.info("Shutting down...")


def _ensure_initial_setup(client):
    """Ensure collections and graph exist (idempotent setup)."""
    try:
        # Check existing collections
        result = client.execute("SHOW COLLECTIONS;")
        collections = [row.get("name") for row in (result.rows if hasattr(result, "rows") else [])]

        if "professor_users" not in collections:
            client.execute("CREATE COLLECTION professor_users;")
            logger.info("✅ Created collection: professor_users")

        if "professor_follows" not in collections:
            client.execute("CREATE COLLECTION professor_follows;")
            logger.info("✅ Created collection: professor_follows")

        # Create live graph and mappings (idempotent)
        client.execute("CREATE LIVE GRAPH professor_social HETEROGENEOUS DIRECTED;")
        client.execute("MAP NODE User FROM professor_users KEY _id PROPERTIES username;")
        client.execute("MAP EDGE FOLLOWS FROM professor_follows SOURCE from_id AS User TARGET to_id AS User DIRECTED;")
        logger.info("✅ LiveGraph professor_social is ready")

    except Exception as e:
        logger.warning(f"Initial setup warning: {e}")
        # This is safe to ignore if setup already exists

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Dependency Injection
# ============================================================================

def get_client():
    """Dependency for getting the NexoraDB client."""
    return app.state.client

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Check the health of the service and database connectivity."""
    client = get_client()
    try:
        connected = client.ping()
        return HealthResponse(
            status="healthy" if connected else "unhealthy",
            database_connected=connected,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            version="1.0.0"
        )

# ============================================================================
# Import Endpoint
# ============================================================================

@app.post("/api/v1/imports/relationships")
async def import_file(
    file: UploadFile = File(...),
    client=Depends(get_client)
) -> ImportResponse:
    """Import a three-column relationship file.

    The file format is:
    U01 U02 1
    U01 U03 1
    U02 U03 1

    Rules:
    - Flag must be exactly "1" (mutual relationship)
    - Self-loops are rejected
    - Reverse duplicates are detected and skipped
    - Each unique pair creates two directed edges
    """
    # Validate file size
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed limit of {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Validate encoding
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be encoded in UTF-8"
        )

    # Process and validate
    result = process_import(text)

    if not result.success:
        return result

    # Execute queries
    queries = generate_insert_queries(text)
    for query in queries:
        try:
            client.execute(query)
        except NexoraDBQueryError as e:
            result.errors.append(str(e))
            return result

    logger.info(
        f"Import completed: {result.unique_users} users, "
        f"{result.unique_pairs} pairs, {result.directed_edges_created} directed edges"
    )
    return result

# ============================================================================
# User CRUD Endpoints
# ============================================================================

@app.get("/api/v1/users")
async def list_users(
    limit: int = 1000,
    client=Depends(get_client)
):
    """List all users with optional limit."""
    repo = UserRepository(client)
    return {"items": repo.get_all(limit), "total": repo.count()}


@app.post("/api/v1/users")
async def create_user(
    user: UserCreate,
    client=Depends(get_client)
):
    """Create a new user."""
    repo = UserRepository(client)

    # Check if user already exists
    existing = repo.get_by_id(user._id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": f"User '{user._id}' already exists"}
        )

    username = user.username or user._id
    return repo.create(user._id, username)


@app.put("/api/v1/users/{user_id}")
async def update_user(
    user_id: str,
    update: UserUpdate,
    client=Depends(get_client)
):
    """Update a user's username."""
    repo = UserRepository(client)

    existing = repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"User '{user_id}' not found"}
        )

    return repo.update(user_id, update.username)


@app.delete("/api/v1/users/{user_id}")
async def delete_user(
    user_id: str,
    client=Depends(get_client)
):
    """Delete a user and all associated relationships."""
    repo = UserRepository(client)

    existing = repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"User '{user_id}' not found"}
        )

    repo.delete(user_id)
    return {"deleted": True, "user_id": user_id}

# ============================================================================
# Relationship CRUD Endpoints
# ============================================================================

@app.get("/api/v1/relationships")
async def list_relationships(
    limit: int = 1000,
    client=Depends(get_client)
):
    """List all unique relationship pairs."""
    repo = RelationshipRepository(client)
    return {"items": repo.get_all_pairs(limit), "total": repo.count_pairs()}


@app.post("/api/v1/relationships")
async def create_relationship(
    rel: RelationshipCreate,
    client=Depends(get_client)
):
    """Create a two-way relationship between two users."""
    repo = RelationshipRepository(client)

    # Check if relationship already exists
    if repo.exists(rel.user_a, rel.user_b):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": f"Relationship between {rel.user_a} and {rel.user_b} already exists"}
        )

    return repo.create(rel.user_a, rel.user_b)


@app.delete("/api/v1/relationships/{user_a}/{user_b}")
async def delete_relationship(
    user_a: str,
    user_b: str,
    client=Depends(get_client)
):
    """Delete a two-way relationship between two users."""
    repo = RelationshipRepository(client)

    if not repo.exists(user_a, user_b):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Relationship between {user_a} and {user_b} not found"}
        )

    repo.delete(user_a, user_b)
    return {"deleted": True, "user_a": user_a, "user_b": user_b}

# ============================================================================
# Graph Endpoints
# ============================================================================

@app.get("/api/v1/graph")
async def get_graph(
    limit: int = 500,
    client=Depends(get_client)
):
    """Get a graph snapshot for visualization."""
    repo = GraphRepository(client)
    return repo.get_snapshot(limit)


@app.get("/api/v1/graph/stats")
async def get_graph_stats(
    client=Depends(get_client)
):
    """Get graph statistics."""
    repo = GraphRepository(client)
    return repo.get_stats()

# ============================================================================
# Algorithm Endpoints
# ============================================================================

@app.get("/api/v1/algorithms")
async def list_algorithms():
    """List all available algorithms."""
    return {
        "algorithms": list(ALL_ALGORITHMS.keys()),
        "lock": list(LOCK_ALGORITHMS.keys()),
        "job": list(JOB_ALGORITHMS.keys())
    }


@app.get("/api/v1/algorithms/{name}/params")
async def get_algorithm_params(name: str):
    """Get parameter definitions for a specific algorithm."""
    service = AlgorithmService(get_client())
    try:
        return {"params": service.get_algorithm_params(name)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/algorithms/{name}")
async def run_algorithm(
    name: str,
    request: AlgorithmRequest,
    client=Depends(get_client)
) -> AlgorithmResponse:
    """Execute a specific algorithm with given parameters."""
    service = AlgorithmService(client)

    try:
        return service.execute_algorithm(name, request.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NexoraDBQueryError as e:
        raise HTTPException(status_code=502, detail=str(e))

# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None
    }