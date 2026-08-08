from __future__ import annotations

import json
import threading
from collections import Counter
from typing import Any

from nexoradb.api import NexoraDBAuthError, NexoraDBError, connect

from .file_parser import ParsedFile, RelationshipPair
from .settings import Settings


USERS = "professor_users"
FOLLOWS = "professor_follows"
GRAPH = "professor_social"
EDGE_TYPE = "FOLLOWS"
NODE_TYPE = "User"


class ServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


def q(value: str) -> str:
    """Quote one NexoraQL string literal."""
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _statement(result: Any) -> dict[str, Any]:
    raw = result.raw if isinstance(result.raw, dict) else {}
    statements = raw.get("statements", [])
    if not statements or not isinstance(statements[0], dict):
        raise ServiceError("پاسخ دریافتی از NexoraDB قابل تشخیص نیست.", 502)
    statement = statements[0]
    if not statement.get("success", False):
        raise ServiceError(str(statement.get("error") or "عملیات دیتابیس ناموفق بود."), 502)
    return statement


class NexoraSocialService:
    """All database access is isolated here and goes through the public driver."""

    def __init__(self, settings: Settings) -> None:
        settings.validate()
        self.db = connect(
            url=settings.nexoradb_url,
            token=settings.nexoradb_app_token,
            timeout=settings.nexoradb_timeout,
        )
        self._write_lock = threading.RLock()
        self._ready = False

    def ping(self) -> bool:
        return self.db.ping()

    def ensure_schema(self) -> None:
        if self._ready:
            return
        with self._write_lock:
            if self._ready:
                return
            collections = {str(row.get("name")) for row in self.db.list_collections().rows}
            if USERS not in collections:
                _statement(self.db.create_collection(USERS))
            if FOLLOWS not in collections:
                _statement(self.db.create_collection(FOLLOWS))

            graphs = {str(row.get("name")) for row in self.db.execute("SHOW GRAPHS;").rows}
            if GRAPH not in graphs:
                setup = self.db.execute(
                    f"""
                    CREATE LIVE GRAPH {GRAPH} HETEROGENEOUS DIRECTED;
                    MAP NODE {NODE_TYPE} FROM {USERS} KEY _id PROPERTIES username;
                    MAP EDGE {EDGE_TYPE} FROM {FOLLOWS}
                        SOURCE from_id AS {NODE_TYPE}
                        TARGET to_id AS {NODE_TYPE}
                        DIRECTED;
                    """
                )
                raw = setup.raw if isinstance(setup.raw, dict) else {}
                failed = [s for s in raw.get("statements", []) if not s.get("success")]
                if failed:
                    raise ServiceError(f"ساخت schema گراف ناموفق بود: {failed}", 502)
            self._ready = True

    def _execute(self, query: str) -> tuple[dict[str, Any], int]:
        self.ensure_schema()
        result = self.db.execute(query)
        return _statement(result), result.execution_time_ms

    def list_users(self, limit: int = 1000) -> list[dict[str, Any]]:
        self.ensure_schema()
        result = self.db.execute(f"SELECT * FROM {USERS} LIMIT {limit};")
        _statement(result)
        return [dict(row) for row in result.rows]

    def user_exists(self, user_id: str) -> bool:
        statement, _ = self._execute(f"EXISTS IN {USERS} WHERE _id = {q(user_id)};")
        return bool(statement.get("exists"))

    def create_user(self, user_id: str, username: str | None = None) -> dict[str, Any]:
        with self._write_lock:
            if self.user_exists(user_id):
                raise ServiceError("این کاربر از قبل وجود دارد.", 409)
            document = {"_id": user_id, "username": username or user_id}
            self.ensure_schema()
            _statement(self.db.insert_one(USERS, document))
            return document

    def update_user(self, user_id: str, username: str) -> dict[str, Any]:
        with self._write_lock:
            if not self.user_exists(user_id):
                raise ServiceError("کاربر پیدا نشد.", 404)
            self._execute(
                f"UPDATE {USERS} SET username={q(username.strip())} WHERE _id = {q(user_id)};"
            )
            return {"_id": user_id, "username": username.strip()}

    def delete_user(self, user_id: str) -> dict[str, int]:
        with self._write_lock:
            if not self.user_exists(user_id):
                raise ServiceError("کاربر پیدا نشد.", 404)
            related = [
                edge
                for edge in self._all_directed_edges()
                if edge.get("from_id") == user_id or edge.get("to_id") == user_id
            ]
            for edge in related:
                self._execute(f"DELETE FROM {FOLLOWS} WHERE _id = {q(str(edge['_id']))};")
            self._execute(f"DELETE FROM {USERS} WHERE _id = {q(user_id)};")
            return {"users_deleted": 1, "directed_edges_deleted": len(related)}

    def _all_directed_edges(self, limit: int = 10000) -> list[dict[str, Any]]:
        self.ensure_schema()
        result = self.db.execute(f"SELECT * FROM {FOLLOWS} LIMIT {limit};")
        _statement(result)
        return [dict(row) for row in result.rows]

    @staticmethod
    def _edge_documents(pair: RelationshipPair) -> tuple[dict[str, str], dict[str, str]]:
        base = pair.pair_id
        common = {"pair_id": base}
        return (
            {
                "_id": f"rel_{base}_ab",
                **common,
                "from_id": pair.user_a,
                "to_id": pair.user_b,
            },
            {
                "_id": f"rel_{base}_ba",
                **common,
                "from_id": pair.user_b,
                "to_id": pair.user_a,
            },
        )

    def list_relationships(self) -> list[dict[str, str]]:
        pairs: dict[str, dict[str, str]] = {}
        for edge in self._all_directed_edges():
            pair = RelationshipPair.normalized(str(edge["from_id"]), str(edge["to_id"]))
            pairs[pair.pair_id] = {
                "pair_id": pair.pair_id,
                "user_a": pair.user_a,
                "user_b": pair.user_b,
            }
        return [pairs[key] for key in sorted(pairs)]

    def relationship_exists(self, pair: RelationshipPair) -> bool:
        statement, _ = self._execute(
            f"EXISTS IN {FOLLOWS} WHERE pair_id = {q(pair.pair_id)};"
        )
        return bool(statement.get("exists"))

    def create_relationship(self, first: str, second: str) -> dict[str, Any]:
        pair = RelationshipPair.normalized(first, second)
        if pair.user_a == pair.user_b:
            raise ServiceError("ارتباط کاربر با خودش مجاز نیست.")
        with self._write_lock:
            if not self.user_exists(pair.user_a) or not self.user_exists(pair.user_b):
                raise ServiceError("هر دو کاربر باید قبل از ایجاد ارتباط وجود داشته باشند.", 404)
            if self.relationship_exists(pair):
                raise ServiceError("این ارتباط از قبل وجود دارد.", 409)
            first_doc, second_doc = self._edge_documents(pair)
            self.ensure_schema()
            _statement(self.db.insert_one(FOLLOWS, first_doc))
            try:
                _statement(self.db.insert_one(FOLLOWS, second_doc))
            except Exception:
                self._execute(f"DELETE FROM {FOLLOWS} WHERE _id = {q(first_doc['_id'])};")
                raise
            return {"pair_id": pair.pair_id, "directed_edges_created": 2}

    def delete_relationship(self, first: str, second: str) -> dict[str, Any]:
        pair = RelationshipPair.normalized(first, second)
        with self._write_lock:
            documents = self._edge_documents(pair)
            existing_ids = {str(edge["_id"]) for edge in self._all_directed_edges()}
            targets = [doc["_id"] for doc in documents if doc["_id"] in existing_ids]
            if not targets:
                raise ServiceError("ارتباط پیدا نشد.", 404)
            for edge_id in targets:
                self._execute(f"DELETE FROM {FOLLOWS} WHERE _id = {q(edge_id)};")
            return {"pair_id": pair.pair_id, "directed_edges_deleted": len(targets)}

    def import_parsed(self, parsed: ParsedFile) -> dict[str, int]:
        created_users = 0
        created_pairs = 0
        existing_users = {str(item["_id"]) for item in self.list_users(limit=10000)}
        existing_pairs = {item["pair_id"] for item in self.list_relationships()}
        with self._write_lock:
            for user_id in parsed.users:
                if user_id not in existing_users:
                    self.create_user(user_id)
                    created_users += 1
            for pair in parsed.pairs:
                if pair.pair_id not in existing_pairs:
                    self.create_relationship(pair.user_a, pair.user_b)
                    created_pairs += 1
        return {
            "lines_read": parsed.lines_read,
            "unique_users_in_file": len(parsed.users),
            "unique_pairs_in_file": len(parsed.pairs),
            "users_created": created_users,
            "pairs_created": created_pairs,
            "directed_edges_created": created_pairs * 2,
            "duplicates_skipped": parsed.duplicates_skipped,
        }

    def graph_view(self) -> dict[str, Any]:
        users = self.list_users(limit=10000)
        relationships = self.list_relationships()
        degrees = Counter()
        for edge in relationships:
            degrees[edge["user_a"]] += 1
            degrees[edge["user_b"]] += 1
        return {
            "nodes": [
                {
                    "id": str(user["_id"]),
                    "label": str(user.get("username") or user["_id"]),
                    "degree": degrees[str(user["_id"])],
                }
                for user in users
            ],
            "edges": [
                {"source": edge["user_a"], "target": edge["user_b"]}
                for edge in relationships
            ],
        }

    def dashboard(self) -> dict[str, Any]:
        graph = self.graph_view()
        return {
            "database_connected": True,
            "users": len(graph["nodes"]),
            "mutual_relationships": len(graph["edges"]),
            "directed_edges": len(graph["edges"]) * 2,
        }

    def run_algorithm(self, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        query = build_algorithm_query(name, parameters)
        statement, elapsed = self._execute(query)
        return {
            "algorithm": name,
            "result": statement.get("result", {}),
            "execution_time_ms": elapsed,
            "engine_elapsed_ms": statement.get("elapsed_ms", 0),
        }


def _required_text(params: dict[str, Any], key: str) -> str:
    value = str(params.get(key, "")).strip()
    if not value:
        raise ServiceError(f"پارامتر {key} الزامی است.")
    return value


def _int(params: dict[str, Any], key: str, default: int, minimum: int = 1, maximum: int = 10000) -> int:
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ServiceError(f"پارامتر {key} باید عدد صحیح باشد.") from exc
    if not minimum <= value <= maximum:
        raise ServiceError(f"پارامتر {key} باید بین {minimum} و {maximum} باشد.")
    return value


def _float(params: dict[str, Any], key: str, default: float) -> float:
    try:
        value = float(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ServiceError(f"پارامتر {key} باید عدد باشد.") from exc
    if not 0.0 <= value <= 1.0:
        raise ServiceError(f"پارامتر {key} باید بین صفر و یک باشد.")
    return value


def build_algorithm_query(name: str, params: dict[str, Any]) -> str:
    if name == "GetFriends":
        user, limit = _required_text(params, "user"), _int(params, "limit", 100)
        return f"RUN LOCK GetFriends ON {GRAPH} WITH user={q(user)}, edge_type={q(EDGE_TYPE)} LIMIT {limit};"
    if name == "AreConnected":
        u1, u2 = _required_text(params, "user1"), _required_text(params, "user2")
        return f"RUN LOCK AreConnected ON {GRAPH} WITH user1={q(u1)}, user2={q(u2)}, edge_type={q(EDGE_TYPE)};"
    if name == "ShortestPath":
        source, target = _required_text(params, "from"), _required_text(params, "to")
        return f"RUN LOCK ShortestPath ON {GRAPH} WITH from={q(source)}, to={q(target)}, edge_type={q(EDGE_TYPE)};"
    if name == "MutualFriends":
        u1, u2 = _required_text(params, "user1"), _required_text(params, "user2")
        return f"RUN LOCK MutualFriends ON {GRAPH} WITH user1={q(u1)}, user2={q(u2)}, edge_type={q(EDGE_TYPE)};"
    if name == "FriendSuggestion":
        user, limit = _required_text(params, "user"), _int(params, "limit", 10)
        return f"RUN LOCK FriendSuggestion ON {GRAPH} WITH user={q(user)}, edge_type={q(EDGE_TYPE)} LIMIT {limit};"
    if name == "MostConnected":
        metric = str(params.get("metric", "total"))
        if metric not in {"in", "out", "total"}:
            raise ServiceError("metric باید in، out یا total باشد.")
        limit = _int(params, "limit", 10)
        return f"RUN LOCK MostConnected ON {GRAPH} WITH metric={q(metric)}, node_type={q(NODE_TYPE)} LIMIT {limit};"
    if name == "NetworkStats":
        return f"RUN LOCK NetworkStats ON {GRAPH} WITH mode='full';"
    if name == "ConnectedComponents":
        return f"RUN JOB ConnectedComponents ON {GRAPH} WITH node_type={q(NODE_TYPE)};"
    if name == "AllDistances":
        source = _required_text(params, "source")
        max_hops = _int(params, "max_hops", 100, minimum=1)
        return f"RUN JOB AllDistances ON {GRAPH} WITH source={q(source)}, max_hops={max_hops}, node_type={q(NODE_TYPE)};"
    if name == "BetweennessCentrality":
        top = _int(params, "top", 10, maximum=1000)
        return f"RUN JOB BetweennessCentrality ON {GRAPH} RETURNS TOP {top};"
    if name == "CommunityDetection":
        iterations = _int(params, "max_iterations", 30, maximum=1000)
        min_size = _int(params, "min_community_size", 2, maximum=10000)
        return (
            f"RUN JOB CommunityDetection ON {GRAPH} WITH max_iterations={iterations}, "
            f"min_community_size={min_size}, members=true, node_type={q(NODE_TYPE)};"
        )
    if name == "InfluenceMaximization":
        k = _int(params, "k", 3, maximum=1000)
        simulations = _int(params, "simulations", 25, maximum=10000)
        probability = _float(params, "probability", 0.2)
        return (
            f"RUN JOB InfluenceMaximization ON {GRAPH} WITH k={k}, simulations={simulations}, "
            f"probability={probability};"
        )
    raise ServiceError("الگوریتم انتخاب‌شده پشتیبانی نمی‌شود.", 404)


DRIVER_ERRORS = (NexoraDBError, NexoraDBAuthError)

