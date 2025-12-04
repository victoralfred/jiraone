#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for jiraone.users module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from jiraone.users import User, UserSearchResult, UserManager


class TestUser:
    """Tests for User dataclass."""

    def test_user_creation(self):
        """Test creating a User instance."""
        user = User(
            account_id="abc123",
            account_type="atlassian",
            display_name="John Doe",
            active=True,
            email="john@example.com",
        )

        assert user.account_id == "abc123"
        assert user.account_type == "atlassian"
        assert user.display_name == "John Doe"
        assert user.active is True
        assert user.email == "john@example.com"

    def test_user_without_email(self):
        """Test creating a User without email."""
        user = User(
            account_id="abc123",
            account_type="atlassian",
            display_name="John Doe",
            active=True,
        )

        assert user.email is None

    def test_to_dict(self):
        """Test converting User to dictionary."""
        user = User(
            account_id="abc123",
            account_type="atlassian",
            display_name="John Doe",
            active=True,
            email="john@example.com",
        )

        result = user.to_dict()

        assert result["accountId"] == "abc123"
        assert result["accountType"] == "atlassian"
        assert result["displayName"] == "John Doe"
        assert result["active"] is True
        assert result["email"] == "john@example.com"

    def test_mention(self):
        """Test generating mention format."""
        user = User(
            account_id="abc123",
            account_type="atlassian",
            display_name="John Doe",
            active=True,
        )

        assert user.mention() == "[~accountId:abc123]"


class TestUserSearchResult:
    """Tests for UserSearchResult."""

    def test_empty_result(self):
        """Test empty search result."""
        result = UserSearchResult()

        assert len(result) == 0
        assert result.total == 0
        assert list(result) == []

    def test_result_with_users(self):
        """Test result with users."""
        users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
        ]
        result = UserSearchResult(users=users, total=2)

        assert len(result) == 2
        assert result.total == 2

    def test_iteration(self):
        """Test iterating over results."""
        users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
        ]
        result = UserSearchResult(users=users, total=2)

        names = [u.display_name for u in result]
        assert names == ["Alice", "Bob"]


class TestUserManager:
    """Tests for UserManager class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        client = Mock()
        client.base_url = "https://test.atlassian.net"
        return client

    @pytest.fixture
    def mock_endpoint(self):
        """Create a mock endpoint builder."""
        endpoint = Mock()
        endpoint.myself.return_value = "/rest/api/3/myself"
        endpoint.search_users.return_value = "/rest/api/3/users/search"
        endpoint.get_user_group.return_value = "/rest/api/3/user/groups"
        return endpoint

    @pytest.fixture
    def user_manager(self, mock_client, mock_endpoint):
        """Create a UserManager with mocked dependencies."""
        return UserManager(client=mock_client, endpoint=mock_endpoint)

    def test_fetch_users_success(self, user_manager, mock_client):
        """Test fetching users successfully."""
        # Mock successful validation
        mock_client.get.return_value = Mock(status_code=200)

        # Mock user data
        user_data = [
            {
                "accountId": "id1",
                "accountType": "atlassian",
                "displayName": "Alice",
                "active": True,
            },
            {
                "accountId": "id2",
                "accountType": "atlassian",
                "displayName": "Bob",
                "active": False,
            },
        ]

        # First call validates, second returns users, third returns empty
        mock_client.get.side_effect = [
            Mock(status_code=200),  # myself()
            Mock(content=json.dumps(user_data).encode()),  # search_users
            Mock(content=json.dumps([]).encode()),  # empty result
        ]

        users = user_manager.fetch_users()

        assert len(users) == 2
        assert users[0].display_name == "Alice"
        assert users[1].display_name == "Bob"

    def test_fetch_users_active_only(self, user_manager, mock_client):
        """Test fetching only active users."""
        user_data = [
            {"accountId": "id1", "accountType": "atlassian", "displayName": "Alice", "active": True},
            {"accountId": "id2", "accountType": "atlassian", "displayName": "Bob", "active": False},
        ]

        mock_client.get.side_effect = [
            Mock(status_code=200),
            Mock(content=json.dumps(user_data).encode()),
            Mock(content=json.dumps([]).encode()),
        ]

        users = user_manager.fetch_users(status="active")

        assert len(users) == 1
        assert users[0].display_name == "Alice"

    def test_fetch_users_inactive_only(self, user_manager, mock_client):
        """Test fetching only inactive users."""
        user_data = [
            {"accountId": "id1", "accountType": "atlassian", "displayName": "Alice", "active": True},
            {"accountId": "id2", "accountType": "atlassian", "displayName": "Bob", "active": False},
        ]

        mock_client.get.side_effect = [
            Mock(status_code=200),
            Mock(content=json.dumps(user_data).encode()),
            Mock(content=json.dumps([]).encode()),
        ]

        users = user_manager.fetch_users(status="inactive")

        assert len(users) == 1
        assert users[0].display_name == "Bob"

    def test_fetch_users_connection_error(self, user_manager, mock_client):
        """Test handling connection error."""
        mock_client.get.return_value = Mock(status_code=401, reason="Unauthorized")

        with pytest.raises(ConnectionError):
            user_manager.fetch_users()

    def test_search_by_name(self, user_manager):
        """Test searching users by name."""
        # Pre-populate users
        user_manager._users = [
            User("id1", "atlassian", "Alice Smith", True),
            User("id2", "atlassian", "Bob Jones", True),
            User("id3", "atlassian", "Alice Johnson", True),
        ]

        results = user_manager.search("Alice")

        assert len(results) == 2
        assert all("Alice" in u.display_name for u in results)

    def test_search_by_account_id(self, user_manager):
        """Test searching users by account ID."""
        user_manager._users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
        ]

        results = user_manager.search("id2")

        assert len(results) == 1
        assert results.users[0].display_name == "Bob"

    def test_search_multiple_queries(self, user_manager):
        """Test searching with multiple queries."""
        user_manager._users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
            User("id3", "atlassian", "Charlie", True),
        ]

        results = user_manager.search(["Alice", "Charlie"])

        assert len(results) == 2

    def test_get_user_groups(self, user_manager, mock_client):
        """Test getting user groups."""
        groups_data = [{"name": "developers"}, {"name": "admins"}]
        mock_client.get.return_value = Mock(content=json.dumps(groups_data).encode())

        groups = user_manager.get_user_groups("user123")

        assert groups == ["developers", "admins"]

    def test_get_user_groups_with_user_object(self, user_manager, mock_client):
        """Test getting groups for a User object."""
        user = User("user123", "atlassian", "Test User", True)
        groups_data = [{"name": "developers"}]
        mock_client.get.return_value = Mock(content=json.dumps(groups_data).encode())

        groups = user_manager.get_user_groups(user)

        assert groups == ["developers"]

    def test_mention_users(self, user_manager):
        """Test generating mention strings."""
        user_manager._users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
        ]

        mentions = user_manager.mention_users("Alice")

        assert mentions == ["[~accountId:id1]"]

    def test_mention_multiple_users(self, user_manager):
        """Test generating mentions for multiple users."""
        user_manager._users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", True),
        ]

        mentions = user_manager.mention_users(["Alice", "Bob"])

        assert "[~accountId:id1]" in mentions
        assert "[~accountId:id2]" in mentions

    def test_export_to_csv(self, user_manager, tmp_path):
        """Test exporting users to CSV."""
        user_manager._users = [
            User("id1", "atlassian", "Alice", True),
            User("id2", "atlassian", "Bob", False),
        ]

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            path = user_manager.export_to_csv("exports", "users.csv")

        assert "users.csv" in path
        assert (tmp_path / "exports" / "users.csv").exists()
