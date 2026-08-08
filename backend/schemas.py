"""Pydantic schemas for request/response validation."""

from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    database_connected: bool
    version: str = "1.0.0"


class ImportResponse(BaseModel):
    """Import file processing response schema."""
    lines_read: int
    unique_users: int
    unique_pairs: int
    directed_edges_created: int
    duplicates_skipped: int
    errors: List[str] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if the import was successful."""
        return len(self.errors) == 0


class UserCreate(BaseModel):
    """User creation request schema."""
    _id: str = Field(
        ...,
        alias="id",
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9_\-]+$",
        description="Unique user identifier"
    )
    username: Optional[str] = Field(
        None,
        description="Display name (defaults to _id if not provided)"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username if provided."""
        if v is None:
            return v
        if len(v) < 1:
            return v
        return v


class UserResponse(BaseModel):
    """User response schema."""
    _id: str
    username: str


class UserUpdate(BaseModel):
    """User update request schema."""
    username: str = Field(..., min_length=1, max_length=50)


class RelationshipCreate(BaseModel):
    """Relationship creation request schema."""
    user_a: str = Field(..., min_length=1, pattern=r"^[A-Za-z0-9_\-]+$")
    user_b: str = Field(..., min_length=1, pattern=r"^[A-Za-z0-9_\-]+$")

    @field_validator("user_b")
    @classmethod
    def validate_different(cls, v: str, info) -> str:
        """Ensure user_a and user_b are different."""
        if info.data.get("user_a") == v:
            raise ValueError("user_a and user_b cannot be the same")
        return v


class RelationshipResponse(BaseModel):
    """Relationship response schema."""
    pair_id: str
    user_a: str
    user_b: str


class GraphNode(BaseModel):
    """Graph node for visualization."""
    id: str
    label: str
    degree: int = 0


class GraphEdge(BaseModel):
    """Graph edge for visualization."""
    source: str
    target: str


class GraphSnapshot(BaseModel):
    """Complete graph snapshot for visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int


class AlgorithmRequest(BaseModel):
    """Algorithm execution request schema."""
    params: Dict[str, Any] = Field(default_factory=dict)


class AlgorithmResponse(BaseModel):
    """Algorithm execution response schema."""
    algorithm: str
    result: Any
    execution_time_ms: int
    summary: Optional[str] = None
    raw: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Uniform error response schema."""
    error: Dict[str, Any] = Field(
        default_factory=lambda: {
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "details": None,
            "request_id": None
        }
    )