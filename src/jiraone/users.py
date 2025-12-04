#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User management utilities for jiraone.

This module provides utilities for managing and querying Jira users,
including fetching user lists, searching users, and generating reports.

Example::

    from jiraone import LOGIN
    from jiraone.users import UserManager

    LOGIN(user="email@example.com", password="token", url="https://example.atlassian.net")

    # Create user manager
    users = UserManager()

    # Fetch all active users
    active_users = users.fetch_users(status="active")

    # Search for a specific user
    found = users.search("John Doe")

    # Export users to CSV
    users.export_to_csv("Reports", "users.csv")
"""
import json
import sys
from collections import OrderedDict, deque, namedtuple
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from jiraone.jira_logs import add_log


@dataclass
class User:
    """Represents a Jira user.

    :param account_id: The user's account ID
    :param account_type: Type of account (atlassian, customer, app, unknown)
    :param display_name: The user's display name
    :param active: Whether the user is active
    :param email: Optional email address
    """

    account_id: str
    account_type: str
    display_name: str
    active: bool
    email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "accountId": self.account_id,
            "accountType": self.account_type,
            "displayName": self.display_name,
            "active": self.active,
            "email": self.email,
        }

    def mention(self) -> str:
        """Return the mention format for this user."""
        return f"[~accountId:{self.account_id}]"


@dataclass
class UserSearchResult:
    """Result of a user search operation."""

    users: List[User] = field(default_factory=list)
    total: int = 0

    def __iter__(self) -> Iterator[User]:
        """Iterate over users."""
        return iter(self.users)

    def __len__(self) -> int:
        """Return number of users found."""
        return len(self.users)


class UserManager:
    """Manager for Jira user operations.

    Provides methods to fetch, search, and export user data.

    Example::

        from jiraone import LOGIN
        from jiraone.users import UserManager

        LOGIN(user="email@example.com", password="token",
              url="https://example.atlassian.net")

        manager = UserManager()

        # Fetch all users
        for user in manager.fetch_users():
            print(f"{user.display_name}: {user.account_id}")

        # Search by name
        results = manager.search("John")
        for user in results:
            print(user.mention())
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        endpoint: Optional[Any] = None,
    ) -> None:
        """Initialize UserManager.

        :param client: HTTP client (defaults to LOGIN)
        :param endpoint: Endpoint builder (defaults to jiraone.endpoint)
        """
        self._client = client
        self._endpoint = endpoint
        self._users: List[User] = []

    @property
    def client(self) -> Any:
        """Get the HTTP client."""
        if self._client is None:
            from jiraone import LOGIN

            self._client = LOGIN
        return self._client

    @property
    def endpoint(self) -> Any:
        """Get the endpoint builder."""
        if self._endpoint is None:
            from jiraone import endpoint

            self._endpoint = endpoint
        return self._endpoint

    def fetch_users(
        self,
        status: str = "both",
        account_type: str = "atlassian",
        max_results: int = 1000,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> List[User]:
        """Fetch users from Jira.

        :param status: Filter by status - "both", "active", or "inactive"
        :param account_type: Account type - "atlassian", "customer", "app", "unknown"
        :param max_results: Maximum results per page
        :param progress_callback: Optional callback for progress updates
        :return: List of User objects

        Example::

            # Fetch all active Atlassian users
            users = manager.fetch_users(status="active", account_type="atlassian")

            # Fetch with progress callback
            def on_progress(count):
                print(f"Fetched {count} users so far...")

            users = manager.fetch_users(progress_callback=on_progress)
        """
        self._users = []
        start_at = 0

        # Validate connection
        validate = self.client.get(self.endpoint.myself())
        if validate.status_code != 200:
            add_log(
                f"Login failure on {self.client.base_url}: {validate.reason}",
                "error",
            )
            raise ConnectionError(
                f"Unable to connect to {self.client.base_url}"
            )

        while True:
            response = self.client.get(
                self.endpoint.search_users(start_at, max_results)
            )
            results = json.loads(response.content)

            if not results:
                break

            for user_data in results:
                user = self._parse_user(user_data)
                if self._matches_filter(user, status, account_type):
                    self._users.append(user)

            start_at += max_results

            if progress_callback:
                progress_callback(len(self._users))

            add_log(f"Fetched {len(self._users)} users so far", "info")

        return self._users

    def _parse_user(self, data: Dict[str, Any]) -> User:
        """Parse user data from API response."""
        return User(
            account_id=data.get("accountId", ""),
            account_type=data.get("accountType", "unknown"),
            display_name=data.get("displayName", ""),
            active=data.get("active", False),
            email=data.get("emailAddress"),
        )

    def _matches_filter(
        self,
        user: User,
        status: str,
        account_type: str,
    ) -> bool:
        """Check if user matches the filter criteria."""
        if user.account_type != account_type:
            return False

        if status == "both":
            return True
        elif status == "active":
            return user.active
        elif status == "inactive":
            return not user.active
        return True

    def search(
        self,
        query: Union[str, List[str]],
        users: Optional[List[User]] = None,
    ) -> UserSearchResult:
        """Search for users by display name or account ID.

        :param query: Search query (string or list of strings)
        :param users: Optional list of users to search (defaults to fetched users)
        :return: UserSearchResult with matching users

        Example::

            # Search by name
            results = manager.search("John Doe")

            # Search multiple names
            results = manager.search(["John Doe", "Jane Smith"])
        """
        user_list = users if users is not None else self._users

        if not user_list:
            user_list = self.fetch_users()

        queries = [query] if isinstance(query, str) else query
        found = []

        for user in user_list:
            for q in queries:
                if (
                    q.lower() in user.display_name.lower()
                    or q == user.account_id
                ):
                    found.append(user)
                    break

        return UserSearchResult(users=found, total=len(found))

    def get_user_groups(
        self,
        user: Union[User, str],
    ) -> List[str]:
        """Get groups for a user.

        :param user: User object or account ID
        :return: List of group names

        Example::

            groups = manager.get_user_groups("5b10ac8d82e05b22cc7d4ef5")
            print(f"User is in groups: {groups}")
        """
        account_id = user.account_id if isinstance(user, User) else user
        response = self.client.get(self.endpoint.get_user_group(account_id))
        results = json.loads(response.content)
        return [g["name"] for g in results]

    def export_to_csv(
        self,
        folder: str,
        filename: str,
        users: Optional[List[User]] = None,
        include_groups: bool = False,
    ) -> str:
        """Export users to a CSV file.

        :param folder: Output folder name
        :param filename: Output file name
        :param users: Optional list of users (defaults to fetched users)
        :param include_groups: Include group membership in export
        :return: Path to the created file

        Example::

            # Export all users
            path = manager.export_to_csv("Reports", "users.csv")

            # Export with groups
            path = manager.export_to_csv("Reports", "users_groups.csv",
                                        include_groups=True)
        """
        from jiraone.file_io import file_writer, path_builder

        user_list = users if users is not None else self._users

        if not user_list:
            user_list = self.fetch_users()

        # Write header
        headers = ["AccountId", "AccountType", "DisplayName", "Active"]
        if include_groups:
            headers.append("Groups")

        file_writer(folder, filename, headers, mode="w")

        # Write data
        for user in user_list:
            row = [
                user.account_id,
                user.account_type,
                user.display_name,
                str(user.active),
            ]
            if include_groups:
                groups = self.get_user_groups(user)
                row.append(", ".join(groups))

            file_writer(folder, filename, row)

        path = path_builder(folder, filename)
        add_log(f"Exported {len(user_list)} users to {path}", "info")
        return path

    def mention_users(
        self,
        names: Union[str, List[str]],
    ) -> List[str]:
        """Get mention strings for users by name.

        :param names: User name(s) to search for
        :return: List of mention strings

        Example::

            mentions = manager.mention_users("John Doe")
            # Returns: ["[~accountId:abc123]"]

            mentions = manager.mention_users(["John", "Jane"])
            # Returns: ["[~accountId:abc123]", "[~accountId:def456]"]
        """
        results = self.search(names)
        return [user.mention() for user in results]
