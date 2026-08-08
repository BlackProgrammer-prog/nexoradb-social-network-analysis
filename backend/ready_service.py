from __future__ import annotations

from .nexora_service import GRAPH, NexoraSocialService, ServiceError, _statement


class ReadyNexoraSocialService(NexoraSocialService):
    """Ensure the persisted graph has its one-time initial projection."""

    def ensure_schema(self) -> None:
        if self._ready:
            return
        with self._write_lock:
            if self._ready:
                return

            # Creates collections, graph definition and mappings when missing.
            super().ensure_schema()

            try:
                status = _statement(self.db.execute(f"GRAPH STATUS {GRAPH};"))
                if not bool(status.get("ready")):
                    # A LiveGraph still needs one initial projection to become
                    # ready. Afterwards all inserts/updates/deletes are live.
                    built = _statement(self.db.execute(f"BUILD GRAPH {GRAPH};"))
                    if not built.get("success", True):
                        raise ServiceError("آماده‌سازی اولیه LiveGraph ناموفق بود.", 502)
            except Exception:
                self._ready = False
                raise

