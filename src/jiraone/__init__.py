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

Example::

    from jiraone import LOGIN, endpoint

    LOGIN(
        user="your-email@example.com",
        password="your-api-token",
        url="https://your-instance.atlassian.net"
    )

    response = LOGIN.get(endpoint.myself())
    print(response.json())

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
]
