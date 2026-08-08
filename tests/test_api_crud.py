"""Integration tests for API CRUD operations."""

import pytest
import requests

API_URL = "http://localhost:8100"


class TestAPICRUD:
    """Test suite for CRUD operations."""

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_create_user(self):
        """Test user creation."""
        response = requests.post(
            f"{API_URL}/api/v1/users",
            json={"_id": "T01", "username": "test_user"}
        )
        assert response.status_code in [200, 409]  # 200 OK or 409 Conflict

    def test_list_users(self):
        """Test listing users."""
        response = requests.get(f"{API_URL}/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_relationship(self):
        """Test relationship creation."""
        # First create two users
        requests.post(f"{API_URL}/api/v1/users", json={"_id": "R01", "username": "user_a"})
        requests.post(f"{API_URL}/api/v1/users", json={"_id": "R02", "username": "user_b"})

        # Create relationship
        response = requests.post(
            f"{API_URL}/api/v1/relationships",
            json={"user_a": "R01", "user_b": "R02"}
        )
        assert response.status_code in [200, 409]

    def test_list_relationships(self):
        """Test listing relationships."""
        response = requests.get(f"{API_URL}/api/v1/relationships")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data