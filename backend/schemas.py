from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    username: str | None = Field(default=None, max_length=128)

    @field_validator("id")
    @classmethod
    def clean_id(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("شناسه نباید خالی باشد یا فاصله داشته باشد")
        return value


class UserUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=128)


class RelationshipCreate(BaseModel):
    user_a: str = Field(min_length=1, max_length=128)
    user_b: str = Field(min_length=1, max_length=128)

    @field_validator("user_a", "user_b")
    @classmethod
    def clean_user(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("شناسه کاربر نامعتبر است")
        return value


class AlgorithmRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)

