"""Algorithm service for executing graph algorithms on the social graph.

This module defines all 12 algorithms (7 LOCK + 5 JOB) and provides
a safe query builder with whitelist-based parameter validation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, List

from schemas import AlgorithmResponse
from nexora_client import NexoraClient


# ============================================================================
# Algorithm Definitions
# ============================================================================

LOCK_ALGORITHMS = {
    "GetFriends": {
        "query": "RUN LOCK GetFriends ON professor_social WITH user='{user}', edge_type='FOLLOWS' LIMIT {limit};",
        "params": {
            "user": {"type": "str", "required": True, "default": None},
            "limit": {"type": "int", "required": False, "default": 100}
        },
        "summary": "Friends of user {user} (max {limit})"
    },
    "AreConnected": {
        "query": "RUN LOCK AreConnected ON professor_social WITH user1='{user1}', user2='{user2}', edge_type='FOLLOWS';",
        "params": {
            "user1": {"type": "str", "required": True},
            "user2": {"type": "str", "required": True}
        },
        "summary": "Check if {user1} and {user2} are connected"
    },
    "ShortestPath": {
        "query": "RUN LOCK ShortestPath ON professor_social WITH from='{from}', to='{to}', edge_type='FOLLOWS';",
        "params": {
            "from": {"type": "str", "required": True},
            "to": {"type": "str", "required": True}
        },
        "summary": "Shortest path from {from} to {to}"
    },
    "MutualFriends": {
        "query": "RUN LOCK MutualFriends ON professor_social WITH user1='{user1}', user2='{user2}';",
        "params": {
            "user1": {"type": "str", "required": True},
            "user2": {"type": "str", "required": True}
        },
        "summary": "Mutual friends of {user1} and {user2}"
    },
    "FriendSuggestion": {
        "query": "RUN LOCK FriendSuggestion ON professor_social WITH user='{user}', limit={limit};",
        "params": {
            "user": {"type": "str", "required": True},
            "limit": {"type": "int", "required": False, "default": 20}
        },
        "summary": "Friend suggestions for {user}"
    },
    "MostConnected": {
        "query": "RUN LOCK MostConnected ON professor_social WITH metric='out', node_type='User' LIMIT {limit};",
        "params": {
            "limit": {"type": "int", "required": False, "default": 10}
        },
        "summary": "Top {limit} most connected users"
    },
    "NetworkStats": {
        "query": "RUN LOCK NetworkStats ON professor_social WITH mode='full';",
        "params": {},
        "summary": "Complete network statistics"
    }
}

JOB_ALGORITHMS = {
    "ConnectedComponents": {
        "query": "RUN JOB ConnectedComponents ON professor_social;",
        "params": {},
        "summary": "Connected components of the network"
    },
    "AllDistances": {
        "query": "RUN JOB AllDistances ON professor_social WITH source='{source}', max_hops={max_hops};",
        "params": {
            "source": {"type": "str", "required": True},
            "max_hops": {"type": "int", "required": False, "default": 10}
        },
        "summary": "Distances from {source} to all users (max {max_hops} hops)"
    },
    "BetweennessCentrality": {
        "query": "RUN JOB BetweennessCentrality ON professor_social RETURNS TOP {top};",
        "params": {
            "top": {"type": "int", "required": False, "default": 5}
        },
        "summary": "Top {top} users by betweenness centrality"
    },
    "CommunityDetection": {
        "query": "RUN JOB CommunityDetection ON professor_social WITH max_iterations={iterations}, min_size={min_size};",
        "params": {
            "iterations": {"type": "int", "required": False, "default": 10},
            "min_size": {"type": "int", "required": False, "default": 2}
        },
        "summary": "Community detection with {iterations} iterations"
    },
    "InfluenceMaximization": {
        "query": "RUN JOB InfluenceMaximization ON professor_social WITH k={k}, simulations={simulations}, probability={probability};",
        "params": {
            "k": {"type": "int", "required": True, "default": 1},
            "simulations": {"type": "int", "required": False, "default": 100},
            "probability": {"type": "float", "required": False, "default": 0.5}
        },
        "summary": "Top {k} influential users ({simulations} simulations)"
    }
}

ALL_ALGORITHMS = {**LOCK_ALGORITHMS, **JOB_ALGORITHMS}


class AlgorithmService:
    """Service for executing graph algorithms."""

    def __init__(self, client: NexoraClient):
        self._client = client

    def get_algorithm_list(self) -> List[str]:
        """Get list of all available algorithms."""
        return list(ALL_ALGORITHMS.keys())

    def get_algorithm_type(self, name: str) -> str:
        """Get the type of an algorithm (LOCK or JOB)."""
        if name in LOCK_ALGORITHMS:
            return "LOCK"
        if name in JOB_ALGORITHMS:
            return "JOB"
        raise ValueError(f"Algorithm '{name}' not found")

    def get_algorithm_params(self, name: str) -> Dict[str, Any]:
        """Get parameter definitions for an algorithm."""
        if name not in ALL_ALGORITHMS:
            raise ValueError(f"Algorithm '{name}' not found")
        return ALL_ALGORITHMS[name]["params"]

    def build_query(self, name: str, params: Dict[str, Any]) -> str:
        """Build a safe query for an algorithm using whitelist-based validation.

        This method uses a whitelist approach: only known algorithms and
        their predefined parameters are allowed. User input is never
        directly interpolated into queries without validation.
        """
        if name not in ALL_ALGORITHMS:
            raise ValueError(f"Algorithm '{name}' is not supported")

        template = ALL_ALGORITHMS[name]["query"]
        param_defs = ALL_ALGORITHMS[name]["params"]

        # Validate and build query parameters
        query_params = {}
        for param_name, param_def in param_defs.items():
            if param_def["required"] and param_name not in params:
                raise ValueError(f"Parameter '{param_name}' is required")

            value = params.get(param_name, param_def.get("default"))
            if value is None and param_def["required"]:
                raise ValueError(f"Parameter '{param_name}' is required")

            query_params[param_name] = value

        return template.format(**query_params)

    def execute_algorithm(self, name: str, params: Dict[str, Any]) -> AlgorithmResponse:
        """Execute an algorithm and return the result."""
        start_time = time.time()

        # Build and execute the query
        query = self.build_query(name, params)
        result = self._client.execute(query)

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Generate a human-readable summary
        summary = self._generate_summary(name, result)

        return AlgorithmResponse(
            algorithm=name,
            result=result.rows if hasattr(result, "rows") else [],
            execution_time_ms=execution_time_ms,
            summary=summary,
            raw=result
        )

    def _generate_summary(self, name: str, result) -> Optional[str]:
        """Generate a human-readable summary of the algorithm result."""
        rows = result.rows if hasattr(result, "rows") else []

        summaries = {
            "NetworkStats": lambda: (
                f"Users: {rows[0].get('active_nodes')}, "
                f"Edges: {rows[0].get('active_edges')}" if rows else None
            ),
            "GetFriends": lambda: f"{len(rows)} friends found",
            "AreConnected": lambda: (
                f"✅ {rows[0].get('hops', '?')} hops" if rows and rows[0].get("connected")
                else "❌ Not connected"
            ),
            "ShortestPath": lambda: (
                f"Path with {len(rows[0].get('path', []))-1} hops: "
                f"{' → '.join(rows[0].get('path', []))}" if rows else "No path found"
            ),
            "MutualFriends": lambda: f"{len(rows)} mutual friends found",
            "FriendSuggestion": lambda: f"{len(rows)} friend suggestions",
            "MostConnected": lambda: (
                f"Most connected: {rows[0].get('user_id', 'unknown')}" if rows
                else "No results found"
            ),
            "ConnectedComponents": lambda: f"{len(rows)} connected components found",
            "CommunityDetection": lambda: f"{len(rows)} communities found",
            "AllDistances": lambda: (
                f"{sum(1 for r in rows if r.get('distance', -1) >= 0)} reachable users"
                if rows else "No results found"
            ),
        }

        summary_func = summaries.get(name)
        return summary_func() if summary_func else None