#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API endpoint builders for Jira REST API.

This module provides URL builders for all Jira REST API endpoints.
It uses a cleaner dependency injection pattern rather than relying on
global state.

Example::

    from jiraone.endpoints import EndpointBuilder

    # Create an endpoint builder with configuration
    endpoints = EndpointBuilder(
        base_url="https://example.atlassian.net",
        api_version="3"
    )

    # Build endpoint URLs
    url = endpoints.myself()
    url = endpoints.search_users(start_at=0, max_results=50)
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class EndpointConfig:
    """Configuration for endpoint building.

    Attributes:
        base_url: The base URL of the Jira instance.
        api_version: API version to use ("3" or "latest").
    """

    base_url: str
    api_version: str = "3"

    @property
    def api_base(self) -> str:
        """Return the base API URL."""
        return f"{self.base_url}/rest/api/{self.api_version}"

    @property
    def agile_base(self) -> str:
        """Return the base Agile API URL."""
        return f"{self.base_url}/rest/agile/1.0"

    @property
    def servicedesk_base(self) -> str:
        """Return the base Service Desk API URL."""
        return f"{self.base_url}/rest/servicedeskapi"


class EndpointBuilder:
    """URL builder for Jira REST API endpoints.

    This class provides methods to build URLs for various Jira API endpoints
    using dependency injection for configuration.

    Example::

        config = EndpointConfig(
            base_url="https://example.atlassian.net",
            api_version="3"
        )
        builder = EndpointBuilder(config)

        # Or use the shorthand:
        builder = EndpointBuilder.from_url("https://example.atlassian.net")

        # Build URLs
        url = builder.myself()  # /rest/api/3/myself
    """

    def __init__(self, config: EndpointConfig) -> None:
        """Initialize the endpoint builder.

        :param config: Endpoint configuration with base_url and api_version
        """
        self.config = config

    @classmethod
    def from_url(
        cls, base_url: str, api_version: str = "3"
    ) -> "EndpointBuilder":
        """Create an EndpointBuilder from a base URL.

        :param base_url: The base URL of the Jira instance
        :param api_version: API version ("3" or "latest")
        :return: Configured EndpointBuilder instance
        """
        config = EndpointConfig(base_url=base_url, api_version=api_version)
        return cls(config)

    # =========================================================================
    # User Endpoints
    # =========================================================================

    def myself(self) -> str:
        """Return URL for current user info.

        :return: URL string
        """
        return f"{self.config.api_base}/myself"

    def search_users(
        self,
        start_at: int = 0,
        max_results: int = 50,
        default: bool = False,
    ) -> str:
        """Return URL to search users.

        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :param default: Use default user search vs all search
        :return: URL string
        """
        if default:
            return (
                f"{self.config.api_base}/users"
                f"?startAt={start_at}&maxResults={max_results}"
            )
        return (
            f"{self.config.api_base}/users/search"
            f"?startAt={start_at}&maxResults={max_results}"
        )

    def get_user_group(self, account_id: str) -> str:
        """Return URL to get user groups.

        :param account_id: User account ID
        :return: URL string
        """
        return f"{self.config.api_base}/user/groups?accountId={account_id}"

    def jira_user(
        self,
        account_id: Optional[str] = None,
        query: Optional[str] = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> str:
        """Return URL for user operations.

        :param account_id: User account ID for specific user
        :param query: Search query
        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :return: URL string
        """
        if account_id:
            return f"{self.config.api_base}/user?accountId={account_id}"
        if query:
            return (
                f"{self.config.api_base}/user/search"
                f"?query={query}&startAt={start_at}&maxResults={max_results}"
            )
        return f"{self.config.api_base}/user"

    # =========================================================================
    # Project Endpoints
    # =========================================================================

    def get_projects(
        self,
        start_at: int = 0,
        max_results: int = 50,
        **kwargs: Any,
    ) -> str:
        """Return URL to search projects.

        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :param kwargs: Additional query parameters (query, searchBy, action, etc.)
        :return: URL string
        """
        params = [f"startAt={start_at}", f"maxResults={max_results}"]
        for key, value in kwargs.items():
            if value is not None:
                params.append(f"{key}={value}")
        query_string = "&".join(params)
        return f"{self.config.api_base}/project/search?{query_string}"

    def projects(
        self,
        key_or_id: Optional[str] = None,
        method: str = "GET",
    ) -> str:
        """Return URL for project operations.

        :param key_or_id: Project key or ID
        :param method: HTTP method (GET, PUT, DELETE)
        :return: URL string
        """
        if key_or_id:
            return f"{self.config.api_base}/project/{key_or_id}"
        return f"{self.config.api_base}/project"

    def get_roles_for_project(self, project_key_or_id: str) -> str:
        """Return URL to get roles for a project.

        :param project_key_or_id: Project key or ID
        :return: URL string
        """
        return f"{self.config.api_base}/project/{project_key_or_id}/role"

    def get_project_role(
        self, project_key_or_id: str, role_id: Union[str, int]
    ) -> str:
        """Return URL to get a specific project role.

        :param project_key_or_id: Project key or ID
        :param role_id: Role ID
        :return: URL string
        """
        return f"{self.config.api_base}/project/{project_key_or_id}/role/{role_id}"

    # =========================================================================
    # Issue Endpoints
    # =========================================================================

    def issues(
        self,
        issue_key_or_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> str:
        """Return URL for issue operations.

        :param issue_key_or_id: Issue key or ID
        :param query: Query parameters
        :return: URL string
        """
        if issue_key_or_id:
            if query:
                return f"{self.config.api_base}/issue/{issue_key_or_id}?{query}"
            return f"{self.config.api_base}/issue/{issue_key_or_id}"
        return f"{self.config.api_base}/issue"

    def search_issues_jql(
        self,
        query: str,
        start_at: int = 0,
        max_results: int = 50,
        **kwargs: Any,
    ) -> str:
        """Return URL to search issues using JQL.

        :param query: JQL query string
        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :param kwargs: Additional parameters (fields, expand, etc.)
        :return: URL string
        """
        params = [
            f"jql={query}",
            f"startAt={start_at}",
            f"maxResults={max_results}",
        ]
        for key, value in kwargs.items():
            if value is not None:
                params.append(f"{key}={value}")
        query_string = "&".join(params)
        return f"{self.config.api_base}/search?{query_string}"

    def issue_attachments(
        self,
        issue_key_or_id: str,
        attachment_id: Optional[str] = None,
    ) -> str:
        """Return URL for attachment operations.

        :param issue_key_or_id: Issue key or ID
        :param attachment_id: Specific attachment ID
        :return: URL string
        """
        if attachment_id:
            return f"{self.config.api_base}/attachment/{attachment_id}"
        return f"{self.config.api_base}/issue/{issue_key_or_id}/attachments"

    def comment(
        self,
        issue_key_or_id: str,
        comment_id: Optional[str] = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> str:
        """Return URL for comment operations.

        :param issue_key_or_id: Issue key or ID
        :param comment_id: Specific comment ID
        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :return: URL string
        """
        base = f"{self.config.api_base}/issue/{issue_key_or_id}/comment"
        if comment_id:
            return f"{base}/{comment_id}"
        return f"{base}?startAt={start_at}&maxResults={max_results}"

    def work_logs(
        self,
        issue_key_or_id: str,
        worklog_id: Optional[str] = None,
    ) -> str:
        """Return URL for worklog operations.

        :param issue_key_or_id: Issue key or ID
        :param worklog_id: Specific worklog ID
        :return: URL string
        """
        base = f"{self.config.api_base}/issue/{issue_key_or_id}/worklog"
        if worklog_id:
            return f"{base}/{worklog_id}"
        return base

    # =========================================================================
    # Field Endpoints
    # =========================================================================

    def get_field(self) -> str:
        """Return URL to get all fields.

        :return: URL string
        """
        return f"{self.config.api_base}/field"

    def get_resolutions(self) -> str:
        """Return URL to get all resolutions.

        :return: URL string
        """
        return f"{self.config.api_base}/resolution"

    def get_all_priorities(self) -> str:
        """Return URL to get all priorities.

        :return: URL string
        """
        return f"{self.config.api_base}/priority"

    def get_all_issue_types(self) -> str:
        """Return URL to get all issue types.

        :return: URL string
        """
        return f"{self.config.api_base}/issuetype"

    # =========================================================================
    # Agile/Board Endpoints
    # =========================================================================

    def get_board(
        self,
        board_id: Optional[int] = None,
        start_at: int = 0,
        max_results: int = 50,
        **kwargs: Any,
    ) -> str:
        """Return URL for board operations.

        :param board_id: Specific board ID
        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :param kwargs: Additional query parameters
        :return: URL string
        """
        if board_id:
            return f"{self.config.agile_base}/board/{board_id}"
        params = [f"startAt={start_at}", f"maxResults={max_results}"]
        for key, value in kwargs.items():
            if value is not None:
                params.append(f"{key}={value}")
        query_string = "&".join(params)
        return f"{self.config.agile_base}/board?{query_string}"

    def get_all_sprints(
        self,
        board_id: int,
        start_at: int = 0,
        max_results: int = 50,
        state: Optional[str] = None,
    ) -> str:
        """Return URL to get sprints for a board.

        :param board_id: Board ID
        :param start_at: Starting index for pagination
        :param max_results: Maximum results to return
        :param state: Sprint state filter (active, closed, future)
        :return: URL string
        """
        params = [f"startAt={start_at}", f"maxResults={max_results}"]
        if state:
            params.append(f"state={state}")
        query_string = "&".join(params)
        return f"{self.config.agile_base}/board/{board_id}/sprint?{query_string}"

    def get_sprint(self, sprint_id: int) -> str:
        """Return URL for sprint operations.

        :param sprint_id: Sprint ID
        :return: URL string
        """
        return f"{self.config.agile_base}/sprint/{sprint_id}"

    # =========================================================================
    # Service Desk Endpoints
    # =========================================================================

    def get_service_desks(
        self,
        start_at: int = 0,
        limit: int = 50,
    ) -> str:
        """Return URL to get service desks.

        :param start_at: Starting index for pagination
        :param limit: Maximum results to return
        :return: URL string
        """
        return f"{self.config.servicedesk_base}/servicedesk?start={start_at}&limit={limit}"

    def get_sd_by_id(self, service_desk_id: int) -> str:
        """Return URL to get a specific service desk.

        :param service_desk_id: Service desk ID
        :return: URL string
        """
        return f"{self.config.servicedesk_base}/servicedesk/{service_desk_id}"

    # =========================================================================
    # Server Info Endpoints
    # =========================================================================

    def server_info(self) -> str:
        """Return URL to get server info.

        :return: URL string
        """
        return f"{self.config.api_base}/serverInfo"

    def instance_info(self) -> str:
        """Return URL to get instance info (Cloud).

        :return: URL string
        """
        return f"{self.config.base_url}/rest/api/3/instance/license"
