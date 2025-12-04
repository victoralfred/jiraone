#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pytest configuration and shared fixtures for jiraone tests.

This module provides reusable fixtures for testing jiraone components.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Any, Dict, Generator

import requests


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def base_url() -> str:
    """Provide a test base URL."""
    return "https://test.atlassian.net"


@pytest.fixture
def api_token() -> str:
    """Provide a test API token."""
    return "test-api-token-12345"


@pytest.fixture
def user_email() -> str:
    """Provide a test user email."""
    return "test@example.com"


@pytest.fixture
def oauth_token() -> str:
    """Provide a test OAuth bearer token."""
    return "test-oauth-bearer-token"


@pytest.fixture
def project_key() -> str:
    """Provide a test project key."""
    return "TEST"


@pytest.fixture
def issue_key(project_key: str) -> str:
    """Provide a test issue key."""
    return f"{project_key}-123"


@pytest.fixture
def account_id() -> str:
    """Provide a test account ID."""
    return "5b10ac8d82e05b22cc7d4ef5"


# =============================================================================
# Mock Response Fixtures
# =============================================================================

@pytest.fixture
def mock_response() -> Mock:
    """Create a basic mock response object."""
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.headers = {}
    response.text = ""
    response.json.return_value = {}
    return response


@pytest.fixture
def mock_success_response(mock_response: Mock) -> Mock:
    """Create a mock successful response."""
    mock_response.status_code = 200
    mock_response.ok = True
    return mock_response


@pytest.fixture
def mock_error_response(mock_response: Mock) -> Mock:
    """Create a mock error response."""
    mock_response.status_code = 400
    mock_response.ok = False
    mock_response.json.return_value = {
        "errorMessages": ["Bad Request"],
        "errors": {}
    }
    return mock_response


@pytest.fixture
def mock_rate_limit_response(mock_response: Mock) -> Mock:
    """Create a mock rate limit (429) response."""
    mock_response.status_code = 429
    mock_response.ok = False
    mock_response.headers = {"Retry-After": "60"}
    mock_response.json.return_value = {
        "errorMessages": ["Rate limit exceeded"]
    }
    return mock_response


@pytest.fixture
def mock_not_found_response(mock_response: Mock) -> Mock:
    """Create a mock not found (404) response."""
    mock_response.status_code = 404
    mock_response.ok = False
    mock_response.json.return_value = {
        "errorMessages": ["Issue does not exist"]
    }
    return mock_response


@pytest.fixture
def mock_unauthorized_response(mock_response: Mock) -> Mock:
    """Create a mock unauthorized (401) response."""
    mock_response.status_code = 401
    mock_response.ok = False
    mock_response.json.return_value = {
        "errorMessages": ["Unauthorized"]
    }
    return mock_response


@pytest.fixture
def mock_forbidden_response(mock_response: Mock) -> Mock:
    """Create a mock forbidden (403) response."""
    mock_response.status_code = 403
    mock_response.ok = False
    mock_response.json.return_value = {
        "errorMessages": ["You do not have permission"]
    }
    return mock_response


# =============================================================================
# Mock Data Fixtures
# =============================================================================

@pytest.fixture
def sample_user_data(account_id: str, user_email: str) -> Dict[str, Any]:
    """Provide sample user data."""
    return {
        "accountId": account_id,
        "accountType": "atlassian",
        "emailAddress": user_email,
        "displayName": "Test User",
        "active": True,
        "timeZone": "UTC",
    }


@pytest.fixture
def sample_project_data(project_key: str) -> Dict[str, Any]:
    """Provide sample project data."""
    return {
        "id": "10001",
        "key": project_key,
        "name": "Test Project",
        "projectTypeKey": "software",
        "simplified": False,
        "style": "classic",
    }


@pytest.fixture
def sample_issue_data(issue_key: str, project_key: str) -> Dict[str, Any]:
    """Provide sample issue data."""
    return {
        "id": "10001",
        "key": issue_key,
        "self": f"https://test.atlassian.net/rest/api/3/issue/{issue_key}",
        "fields": {
            "summary": "Test Issue",
            "description": "Test description",
            "project": {"key": project_key},
            "issuetype": {"name": "Task"},
            "status": {"name": "Open"},
            "priority": {"name": "Medium"},
        }
    }


@pytest.fixture
def sample_issues_list(sample_issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Provide sample paginated issues response."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [sample_issue_data]
    }


@pytest.fixture
def sample_field_data() -> Dict[str, Any]:
    """Provide sample custom field data."""
    return {
        "id": "customfield_10001",
        "name": "Custom Text Field",
        "custom": True,
        "orderable": True,
        "navigable": True,
        "searchable": True,
        "schema": {
            "type": "string",
            "custom": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
            "customId": 10001
        }
    }


# =============================================================================
# Session and Client Fixtures
# =============================================================================

@pytest.fixture
def mock_session() -> Mock:
    """Create a mock requests session."""
    session = Mock(spec=requests.Session)
    session.headers = {}
    session.auth = None
    session.get = Mock()
    session.post = Mock()
    session.put = Mock()
    session.delete = Mock()
    session.patch = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_requests_get(mock_success_response: Mock) -> Generator:
    """Patch requests.get to return a mock response."""
    with patch("requests.get", return_value=mock_success_response) as mock:
        yield mock


@pytest.fixture
def mock_requests_post(mock_success_response: Mock) -> Generator:
    """Patch requests.post to return a mock response."""
    with patch("requests.post", return_value=mock_success_response) as mock:
        yield mock


# =============================================================================
# Endpoint Builder Fixtures
# =============================================================================

@pytest.fixture
def endpoint_config(base_url: str):
    """Create an EndpointConfig for testing."""
    from jiraone.endpoints import EndpointConfig
    return EndpointConfig(base_url=base_url, api_version="3")


@pytest.fixture
def endpoint_builder(endpoint_config):
    """Create an EndpointBuilder for testing."""
    from jiraone.endpoints import EndpointBuilder
    return EndpointBuilder(endpoint_config)


# =============================================================================
# Client Fixtures
# =============================================================================

@pytest.fixture
def client_config():
    """Create a ClientConfig for testing."""
    from jiraone.client import ClientConfig
    return ClientConfig(
        pool_connections=5,
        pool_maxsize=5,
        max_retries=2,
        timeout=10,
    )


@pytest.fixture
def jira_client(base_url: str, user_email: str, api_token: str, client_config):
    """Create a JiraClient for testing."""
    from jiraone.client import JiraClient
    client = JiraClient(
        base_url=base_url,
        user=user_email,
        token=api_token,
        config=client_config,
    )
    yield client
    client.close()


# =============================================================================
# Temporary File Fixtures
# =============================================================================

@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file path."""
    return tmp_path / "test_export.csv"


@pytest.fixture
def temp_download_file(tmp_path):
    """Create a temporary download file path."""
    return tmp_path / "test_download.bin"


# =============================================================================
# Retry Configuration Fixtures
# =============================================================================

@pytest.fixture
def retry_config():
    """Create a RetryConfig for testing."""
    from jiraone.retry import RetryConfig
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
    )
