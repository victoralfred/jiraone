#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Input validation utilities for jiraone.

This module provides functions and classes for validating and sanitizing
user input before it's used in API requests, particularly for URLs and
path components.

Security features:
    - URL validation with HTTPS enforcement
    - Path component sanitization
    - Query parameter validation
    - Protection against injection attacks

Example::

    from jiraone.validation import validate_url, sanitize_path_component

    # Validate URLs
    url = validate_url("https://example.atlassian.net")

    # Sanitize path components
    safe_key = sanitize_path_component("PROJECT-123")
"""
import re
import warnings
from typing import Optional, Union
from urllib.parse import quote, urlparse, urlunparse

from jiraone.exceptions import JiraValidationError


# Valid characters for Jira identifiers
JIRA_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9]*-\d+$')
PROJECT_KEY_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')
ACCOUNT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9:_\-]+$')

# Characters that must be URL encoded in path components
UNSAFE_PATH_CHARS = re.compile(r'[<>"\'\{\}\[\]\|\\^`\s]')


def validate_url(
    url: str,
    require_https: bool = True,
    allowed_hosts: Optional[list] = None,
    warn_http: bool = True,
) -> str:
    """Validate and normalize a URL.

    :param url: The URL to validate
    :param require_https: Whether to require HTTPS (default: True)
    :param allowed_hosts: List of allowed hostnames (optional)
    :param warn_http: Whether to warn about HTTP URLs (default: True)

    :return: Validated and normalized URL

    :raises JiraValidationError: If URL is invalid or doesn't meet requirements

    Example::

        from jiraone.validation import validate_url

        # Basic validation
        url = validate_url("https://example.atlassian.net")

        # Allow HTTP for development
        url = validate_url("http://localhost:8080", require_https=False)

        # Restrict to specific hosts
        url = validate_url(
            "https://mycompany.atlassian.net",
            allowed_hosts=["mycompany.atlassian.net"]
        )
    """
    if not url:
        raise JiraValidationError(
            message="URL cannot be empty",
            field="url",
            value=url,
        )

    # Normalize the URL
    url = url.strip()

    # Parse to check for existing scheme
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise JiraValidationError(
            message=f"Invalid URL format: {e}",
            field="url",
            value=url,
        )

    # Check if URL has a scheme
    if parsed.scheme:
        # Validate that scheme is http or https
        if parsed.scheme not in ('http', 'https'):
            raise JiraValidationError(
                message=f"Invalid URL scheme: {parsed.scheme}. Use http or https.",
                field="url",
                value=url,
            )
    else:
        # Add https:// if no scheme present
        url = f"https://{url}"
        parsed = urlparse(url)

    # HTTPS enforcement
    if parsed.scheme == 'http':
        if require_https:
            raise JiraValidationError(
                message="HTTPS is required. Use require_https=False for development.",
                field="url",
                value=url,
            )
        elif warn_http:
            warnings.warn(
                f"Using HTTP is not recommended for production: {url}",
                UserWarning,
                stacklevel=2,
            )

    # Check hostname
    if not parsed.netloc:
        raise JiraValidationError(
            message="URL must include a hostname",
            field="url",
            value=url,
        )

    # Check allowed hosts
    if allowed_hosts:
        hostname = parsed.hostname
        if hostname not in allowed_hosts:
            raise JiraValidationError(
                message=f"Host '{hostname}' not in allowed hosts: {allowed_hosts}",
                field="url",
                value=url,
            )

    # Remove trailing slash for consistency
    normalized = urlunparse(parsed)
    if normalized.endswith('/'):
        normalized = normalized.rstrip('/')

    return normalized


def sanitize_path_component(
    value: str,
    allow_slashes: bool = False,
    max_length: int = 256,
) -> str:
    """Sanitize a path component for safe use in URLs.

    :param value: The value to sanitize
    :param allow_slashes: Whether to allow forward slashes (default: False)
    :param max_length: Maximum allowed length (default: 256)

    :return: Sanitized path component

    :raises JiraValidationError: If value is empty or too long

    Example::

        from jiraone.validation import sanitize_path_component

        # Sanitize issue key
        key = sanitize_path_component("PROJECT-123")

        # Allow slashes for multi-part paths
        path = sanitize_path_component("issues/attachments", allow_slashes=True)
    """
    if not value:
        raise JiraValidationError(
            message="Path component cannot be empty",
            field="path",
            value=value,
        )

    value = str(value).strip()

    if len(value) > max_length:
        raise JiraValidationError(
            message=f"Path component too long: {len(value)} > {max_length}",
            field="path",
            value=value,
        )

    # Remove or encode unsafe characters
    if UNSAFE_PATH_CHARS.search(value):
        value = UNSAFE_PATH_CHARS.sub('', value)

    # URL encode the value
    if allow_slashes:
        # Encode everything except slashes
        parts = value.split('/')
        value = '/'.join(quote(part, safe='') for part in parts)
    else:
        value = quote(value, safe='')

    return value


def validate_issue_key(key: str) -> str:
    """Validate a Jira issue key format.

    :param key: The issue key to validate (e.g., "PROJECT-123")

    :return: Validated issue key (uppercased)

    :raises JiraValidationError: If key format is invalid

    Example::

        from jiraone.validation import validate_issue_key

        key = validate_issue_key("test-123")  # Returns "TEST-123"
    """
    if not key:
        raise JiraValidationError(
            message="Issue key cannot be empty",
            field="issue_key",
            value=key,
        )

    key = key.strip().upper()

    if not JIRA_KEY_PATTERN.match(key):
        raise JiraValidationError(
            message=f"Invalid issue key format: '{key}'. Expected format: PROJECT-123",
            field="issue_key",
            value=key,
        )

    return key


def validate_project_key(key: str) -> str:
    """Validate a Jira project key format.

    :param key: The project key to validate

    :return: Validated project key (uppercased)

    :raises JiraValidationError: If key format is invalid

    Example::

        from jiraone.validation import validate_project_key

        key = validate_project_key("myproject")  # Returns "MYPROJECT"
    """
    if not key:
        raise JiraValidationError(
            message="Project key cannot be empty",
            field="project_key",
            value=key,
        )

    key = key.strip().upper()

    if not PROJECT_KEY_PATTERN.match(key):
        raise JiraValidationError(
            message=f"Invalid project key format: '{key}'. "
                    "Must start with a letter and contain only letters, numbers, and underscores.",
            field="project_key",
            value=key,
        )

    return key


def validate_account_id(account_id: str) -> str:
    """Validate an Atlassian account ID format.

    :param account_id: The account ID to validate

    :return: Validated account ID

    :raises JiraValidationError: If account ID format is invalid

    Example::

        from jiraone.validation import validate_account_id

        aid = validate_account_id("557058:12345678-1234-1234-1234-123456789012")
    """
    if not account_id:
        raise JiraValidationError(
            message="Account ID cannot be empty",
            field="account_id",
            value=account_id,
        )

    account_id = account_id.strip()

    if not ACCOUNT_ID_PATTERN.match(account_id):
        raise JiraValidationError(
            message=f"Invalid account ID format: '{account_id}'",
            field="account_id",
            value=account_id,
        )

    return account_id


def validate_jql(jql: str, max_length: int = 10000) -> str:
    """Validate and sanitize a JQL query string.

    Basic validation to ensure the JQL is properly formatted.
    Does not validate JQL syntax.

    :param jql: The JQL query string
    :param max_length: Maximum allowed length (default: 10000)

    :return: Validated JQL string

    :raises JiraValidationError: If JQL is empty or too long

    Example::

        from jiraone.validation import validate_jql

        jql = validate_jql("project = TEST ORDER BY created DESC")
    """
    if not jql:
        raise JiraValidationError(
            message="JQL query cannot be empty",
            field="jql",
            value=jql,
        )

    jql = jql.strip()

    if len(jql) > max_length:
        raise JiraValidationError(
            message=f"JQL query too long: {len(jql)} > {max_length}",
            field="jql",
            value=jql[:100] + "...",
        )

    return jql


def safe_format_url(
    base_url: str,
    path: str,
    **params: Union[str, int]
) -> str:
    """Safely format a URL with path and parameters.

    All path components and parameter values are sanitized.

    :param base_url: The base URL (e.g., "https://example.atlassian.net")
    :param path: The path template (e.g., "/rest/api/3/issue/{key}")
    :param params: Named parameters to substitute in the path

    :return: Formatted URL with sanitized components

    Example::

        from jiraone.validation import safe_format_url

        url = safe_format_url(
            "https://example.atlassian.net",
            "/rest/api/3/issue/{key}",
            key="PROJECT-123"
        )
        # Returns: "https://example.atlassian.net/rest/api/3/issue/PROJECT-123"
    """
    # Validate base URL
    base_url = validate_url(base_url, require_https=False)

    # Sanitize parameters
    safe_params = {}
    for key, value in params.items():
        if isinstance(value, int):
            safe_params[key] = str(value)
        else:
            safe_params[key] = sanitize_path_component(str(value))

    # Format the path
    try:
        formatted_path = path.format(**safe_params)
    except KeyError as e:
        raise JiraValidationError(
            message=f"Missing URL parameter: {e}",
            field="params",
            value=str(params),
        )

    # Combine base URL and path
    if not formatted_path.startswith('/'):
        formatted_path = '/' + formatted_path

    return base_url + formatted_path
