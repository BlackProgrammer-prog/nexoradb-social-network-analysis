"""Repository layer for data access operations.

Each repository encapsulates all queries for a specific domain.
This provides a clean separation between business logic and data access.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from nexora_client import NexoraClient


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, client: NexoraClient):
        self._client = client

    def get_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all users with a limit."""
        return self._client.execute_raw(
            f"SELECT * FROM professor_users LIMIT {limit};"
        )

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single user by ID."""
        rows = self._client.execute_raw(
            f"SELECT * FROM professor_users WHERE _id = '{user_id}';"
        )
        return rows[0] if rows else None

    def create(self, user_id: str, username: str) -> Dict[str, Any]:
        """Create a new user."""
        self._client.execute(
            f"INSERT INTO professor_users VALUES ('{{\"_id\":\"{user_id}\",\"username\":\"{username}\"}}')"
        )
        return {"_id": user_id, "username": username}

    def update(self, user_id: str, username: str) -> Optional[Dict[str, Any]]:
        """Update a user's username."""
        self._client.execute(
            f"UPDATE professor_users SET username = '{username}' WHERE _id = '{user_id}';"
        )
        return self.get_by_id(user_id)

    def delete(self, user_id: str) -> bool:
        """Delete a user and all associated relationships."""
        # Delete related relationships (both directions)
        self._client.execute(
            f"DELETE FROM professor_follows WHERE from_id = '{user_id}' OR to_id = '{user_id}';"
        )
        # Delete the user
        self._client.execute(
            f"DELETE FROM professor_users WHERE _id = '{user_id}';"
        )
        return True

    def count(self) -> int:
        """Count total users."""
        rows = self._client.execute_raw("COUNT FROM professor_users;")
        return int(rows[0].get("count", 0)) if rows else 0


class RelationshipRepository:
    """Repository for relationship-related database operations."""

    def __init__(self, client: NexoraClient):
        self._client = client

    def get_all_pairs(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all unique relationship pairs (each pair once)."""
        rows = self._client.execute_raw(
            f"SELECT DISTINCT pair_id, from_id, to_id FROM professor_follows LIMIT {limit};"
        )

        # Deduplicate by pair_id
        pairs = {}
        for row in rows:
            pair_id = row.get("pair_id")
            if pair_id not in pairs:
                ids = pair_id.split("__")
                pairs[pair_id] = {
                    "pair_id": pair_id,
                    "user_a": ids[0],
                    "user_b": ids[1]
                }
        return list(pairs.values())

    def exists(self, user_a: str, user_b: str) -> bool:
        """Check if a relationship exists between two users."""
        a, b = sorted([user_a, user_b])
        pair_id = f"{a}__{b}"
        rows = self._client.execute_raw(
            f"SELECT COUNT FROM professor_follows WHERE pair_id = '{pair_id}' LIMIT 1;"
        )
        return int(rows[0].get("count", 0)) > 0 if rows else False

    def create(self, user_a: str, user_b: str) -> Dict[str, Any]:
        """Create a two-way relationship between two users."""
        a, b = sorted([user_a, user_b])
        pair_id = f"{a}__{b}"

        self._client.execute(
            f"INSERT INTO professor_follows VALUES ('{{\"_id\":\"rel_{a}_{b}_ab\",\"pair_id\":\"{pair_id}\",\"from_id\":\"{a}\",\"to_id\":\"{b}\"}}')"
        )
        self._client.execute(
            f"INSERT INTO professor_follows VALUES ('{{\"_id\":\"rel_{a}_{b}_ba\",\"pair_id\":\"{pair_id}\",\"from_id\":\"{b}\",\"to_id\":\"{a}\"}}')"
        )

        return {"pair_id": pair_id, "user_a": a, "user_b": b}

    def delete(self, user_a: str, user_b: str) -> bool:
        """Delete a two-way relationship between two users."""
        a, b = sorted([user_a, user_b])
        pair_id = f"{a}__{b}"

        self._client.execute(
            f"DELETE FROM professor_follows WHERE pair_id = '{pair_id}';"
        )
        return True

    def count_edges(self) -> int:
        """Count total directed edges."""
        rows = self._client.execute_raw("COUNT FROM professor_follows;")
        return int(rows[0].get("count", 0)) if rows else 0

    def count_pairs(self) -> int:
        """Count total unique relationship pairs."""
        rows = self._client.execute_raw(
            "SELECT COUNT(DISTINCT pair_id) FROM professor_follows;"
        )
        return int(rows[0].get("count", 0)) if rows else 0


class GraphRepository:
    """Repository for graph-related operations."""

    def __init__(self, client: NexoraClient):
        self._client = client

    def get_snapshot(self, limit: int = 500) -> Dict[str, Any]:
        """Get a graph snapshot for visualization."""
        rows = self._client.execute_raw(
            f"TRAVERSE * FROM professor_social DEPTH 3 LIMIT {limit};"
        )

        nodes = {}
        edges = []

        for row in rows:
            if "node" in row:
                node = row["node"]
                nodes[node["id"]] = {
                    "id": node["id"],
                    "label": node.get("label", node["id"])
                }
            if "edge" in row:
                edge = row["edge"]
                edges.append({
                    "source": edge["source"],
                    "target": edge["target"]
                })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        rows = self._client.execute_raw(
            "RUN LOCK NetworkStats ON professor_social WITH mode='full';"
        )
        return rows[0] if rows else {}