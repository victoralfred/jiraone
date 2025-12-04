#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""jiraone - Atlassian REST API Interface for Jira.

jiraone is a Python library for interacting with the Jira REST API.
It provides a clean interface for generating reports and performing
various Jira operations.

Features:
    * Users/Organization users management
    * Extract Issue history
    * Comments handling
    * Send and download attachments
    * Get time in status of issues
    * Download stats of users in a project and their roles
    * Connection pooling for better performance
    * Automatic retry with exponential backoff
    * Input validation and URL sanitization
    * Streaming downloads for large files
    * Pagination iterators for memory efficiency

Quick Start
-----------

Basic authentication::

    from jiraone import LOGIN, endpoint

    LOGIN(
        user="your-email@example.com",
        password="your-api-token",
        url="https://your-instance.atlassian.net"
    )

    response = LOGIN.get(endpoint.myself())
    print(response.json())

Using connection pooling for better performance::

    from jiraone import JiraClient, ClientConfig

    config = ClientConfig(pool_connections=20, timeout=60)
    with JiraClient(
        base_url="https://your-instance.atlassian.net",
        user="email@example.com",
        token="api-token",
        config=config
    ) as client:
        response = client.get("/rest/api/3/myself")
        print(response.json())

Handling rate limits with retry::

    from jiraone import LOGIN, endpoint, with_retry

    @with_retry(max_attempts=5, base_delay=2.0)
    def get_all_projects():
        return LOGIN.get(endpoint.get_projects())

Iterating over paginated results::

    from jiraone import LOGIN, endpoint, PaginatedAPI

    for project in PaginatedAPI(
        client=LOGIN,
        endpoint_func=endpoint.get_projects,
        results_key="values"
    ):
        print(f"{project['key']}: {project['name']}")

Streaming large file downloads::

    from jiraone import StreamingDownloader

    downloader = StreamingDownloader(
        url="https://example.atlassian.net/attachment/12345",
        auth=("email@example.com", "api-token"),
    )
    downloader.download_to_file("attachment.pdf")

"""
from jiraone.access import LOGIN, endpoint, echo, For, field
from jiraone.jira_logs import add_log, WORK_PATH
from jiraone.reporting import (
    PROJECT,
    USER,
    file_writer,
    file_reader,
    path_builder,
    replacement_placeholder,
    comment,
    delete_attachments,
    issue_export,
)
from jiraone.management import manage
from jiraone.exceptions import (
    JiraOneErrors,
    JiraAuthenticationError,
    JiraAPIError,
    JiraRateLimitError,
    JiraNotFoundError,
    JiraPermissionError,
    JiraValidationError,
    JiraFieldError,
    JiraUserError,
    JiraFileError,
    JiraTimeoutError,
    raise_for_status,
)
from jiraone.pagination import (
    PaginatedAPI,
    SearchResultsIterator,
    paginate,
)
from jiraone.retry import (
    RetryConfig,
    with_retry,
    retry_request,
    RetrySession,
)
from jiraone.validation import (
    validate_url,
    sanitize_path_component,
    validate_issue_key,
    validate_project_key,
    validate_account_id,
    validate_jql,
    safe_format_url,
)
from jiraone.client import (
    JiraClient,
    ClientConfig,
    create_pooled_session,
)
from jiraone.streaming import (
    StreamConfig,
    StreamingDownloader,
    StreamingUploader,
    ChunkedExporter,
    streaming_download,
    stream_json_array,
)
from jiraone.endpoints import (
    EndpointBuilder,
    EndpointConfig,
)
from jiraone.fields import (
    FIELD_TYPES,
    FIELD_SEARCH_KEYS,
    get_field_type,
    get_search_key,
    is_custom_field_id,
    extract_custom_field_number,
)
from jiraone.users import (
    User,
    UserSearchResult,
    UserManager,
)
from jiraone.file_io import (
    path_builder as build_path,
    file_writer as write_file,
    file_reader as read_file,
    replacement_placeholder as replace_placeholder,
)

__author__ = "Prince Nyeche"
__version__ = "0.9.3"
__all__ = [
    # Core
    "LOGIN",
    "endpoint",
    "echo",
    "For",
    "field",
    # Logging
    "add_log",
    "WORK_PATH",
    # Reporting
    "PROJECT",
    "USER",
    "file_writer",
    "file_reader",
    "path_builder",
    "replacement_placeholder",
    "comment",
    "delete_attachments",
    "issue_export",
    # Management
    "manage",
    # Exceptions
    "JiraOneErrors",
    "JiraAuthenticationError",
    "JiraAPIError",
    "JiraRateLimitError",
    "JiraNotFoundError",
    "JiraPermissionError",
    "JiraValidationError",
    "JiraFieldError",
    "JiraUserError",
    "JiraFileError",
    "JiraTimeoutError",
    "raise_for_status",
    # Pagination
    "PaginatedAPI",
    "SearchResultsIterator",
    "paginate",
    # Retry
    "RetryConfig",
    "with_retry",
    "retry_request",
    "RetrySession",
    # Validation
    "validate_url",
    "sanitize_path_component",
    "validate_issue_key",
    "validate_project_key",
    "validate_account_id",
    "validate_jql",
    "safe_format_url",
    # Client
    "JiraClient",
    "ClientConfig",
    "create_pooled_session",
    # Streaming
    "StreamConfig",
    "StreamingDownloader",
    "StreamingUploader",
    "ChunkedExporter",
    "streaming_download",
    "stream_json_array",
    # Endpoints (new API)
    "EndpointBuilder",
    "EndpointConfig",
    # Fields (new API)
    "FIELD_TYPES",
    "FIELD_SEARCH_KEYS",
    "get_field_type",
    "get_search_key",
    "is_custom_field_id",
    "extract_custom_field_number",
    # Users (new API)
    "User",
    "UserSearchResult",
    "UserManager",
    # File I/O (new API)
    "build_path",
    "write_file",
    "read_file",
    "replace_placeholder",
]
