from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    nexoradb_url: str = os.getenv("NEXORADB_URL", "http://127.0.0.1:8000")
    nexoradb_app_token: str = os.getenv("NEXORADB_APP_TOKEN", "")
    nexoradb_timeout: float = float(os.getenv("NEXORADB_TIMEOUT", "30"))

    def validate(self) -> None:
        if not self.nexoradb_app_token:
            raise RuntimeError(
                "NEXORADB_APP_TOKEN is empty. Copy .env.example to .env and set the token."
            )


settings = Settings()

