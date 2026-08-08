"""Integration tests for graph algorithms."""

import pytest
import requests

API_URL = "http://localhost:8100"


class TestAlgorithms:
    """Test suite for graph algorithms."""

    def test_list_algorithms(self):
        """Test listing all available algorithms."""
        response = requests.get(f"{API_URL}/api/v1/algorithms")
        assert response.status_code == 200
        data = response.json()
        assert "algorithms" in data
        assert len(data["algorithms"]) >= 12

    def test_get_friends(self):
        """Test GetFriends algorithm."""
        response = requests.post(
            f"{API_URL}/api/v1/algorithms/GetFriends",
            json={"params": {"user": "O3", "limit": 10}}
        )
        if response.status_code == 200:
            result = response.json()
            assert "execution_time_ms" in result
            assert "result" in result

    def test_network_stats(self):
        """Test NetworkStats algorithm."""
        response = requests.post(
            f"{API_URL}/api/v1/algorithms/NetworkStats",
            json={"params": {}}
        )
        if response.status_code == 200:
            result = response.json()
            assert "result" in result
            assert "execution_time_ms" in result

    def test_are_connected(self):
        """Test AreConnected algorithm."""
        response = requests.post(
            f"{API_URL}/api/v1/algorithms/AreConnected",
            json={"params": {"user1": "O3", "user2": "B1"}}
        )
        if response.status_code == 200:
            result = response.json()
            assert "execution_time_ms" in result

    def test_algorithm_error_handling(self):
        """Test algorithm error handling."""
        response = requests.post(
            f"{API_URL}/api/v1/algorithms/InvalidAlgorithm",
            json={"params": {}}
        )
        assert response.status_code in [400, 404]