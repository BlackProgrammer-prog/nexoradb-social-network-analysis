from __future__ import annotations

import unittest

from backend.nexora_service import ServiceError, build_algorithm_query


class AlgorithmQueryTests(unittest.TestCase):
    def test_all_algorithms_have_safe_builders(self) -> None:
        samples = {
            "GetFriends": {"user": "O3", "limit": 10},
            "AreConnected": {"user1": "A", "user2": "B"},
            "ShortestPath": {"from": "A", "to": "B"},
            "MutualFriends": {"user1": "A", "user2": "B"},
            "FriendSuggestion": {"user": "A", "limit": 5},
            "MostConnected": {"metric": "total", "limit": 5},
            "NetworkStats": {},
            "ConnectedComponents": {},
            "AllDistances": {"source": "A", "max_hops": 10},
            "BetweennessCentrality": {"top": 5},
            "CommunityDetection": {"max_iterations": 30, "min_community_size": 2},
            "InfluenceMaximization": {"k": 1, "simulations": 3, "probability": 1.0},
        }
        for name, params in samples.items():
            with self.subTest(name=name):
                query = build_algorithm_query(name, params)
                self.assertIn(name, query)
                self.assertTrue(query.endswith(";"))

    def test_rejects_unknown_algorithm(self) -> None:
        with self.assertRaises(ServiceError):
            build_algorithm_query("DROP EVERYTHING", {})


if __name__ == "__main__":
    unittest.main()

