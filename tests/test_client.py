#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the client module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from jiraone.client import JiraClient, ClientConfig, create_pooled_session
from jiraone.exceptions import JiraValidationError, JiraAPIError


class TestClientConfig:
    """Tests for ClientConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ClientConfig()
        assert config.pool_connections == 10
        assert config.pool_maxsize == 10
        assert config.max_retries == 3
        assert config.backoff_factor == 0.3
        assert config.timeout == 30
        assert config.verify_ssl is True
        assert config.api_version == "3"
        assert config.retry_status_forcelist == (500, 502, 503, 504)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClientConfig(
            pool_connections=20,
            pool_maxsize=30,
            max_retries=5,
            backoff_factor=0.5,
            timeout=60,
            verify_ssl=False,
            api_version="2",
        )
        assert config.pool_connections == 20
        assert config.pool_maxsize == 30
        assert config.max_retries == 5
        assert config.backoff_factor == 0.5
        assert config.timeout == 60
        assert config.verify_ssl is False
        assert config.api_version == "2"


class TestJiraClient:
    """Tests for JiraClient class."""

    def test_init_with_basic_auth(self):
        """Test initialization with basic auth."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        assert client.base_url == "https://example.atlassian.net"
        assert client.session.auth is not None
        assert not client._closed
        client.close()

    def test_init_with_oauth_token(self):
        """Test initialization with OAuth token."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            oauth_token="bearer-token",
        )
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer bearer-token"
        client.close()

    def test_init_without_auth(self):
        """Test initialization without authentication."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
        )
        assert client.session.auth is None
        assert "Authorization" not in client.session.headers
        client.close()

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = ClientConfig(pool_connections=20, timeout=60)
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
            config=config,
        )
        assert client.config.pool_connections == 20
        assert client.config.timeout == 60
        client.close()

    def test_init_with_existing_session(self):
        """Test initialization with existing session."""
        existing_session = requests.Session()
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
            session=existing_session,
        )
        assert client.session is existing_session
        client.close()

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        client = JiraClient(
            base_url="https://example.atlassian.net/",
            user="test@example.com",
            token="api-token",
        )
        assert client.base_url == "https://example.atlassian.net"
        client.close()

    def test_build_url_with_path(self):
        """Test URL building with path."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        url = client._build_url("/rest/api/3/myself")
        assert url == "https://example.atlassian.net/rest/api/3/myself"
        client.close()

    def test_build_url_with_full_url(self):
        """Test URL building with full URL."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        full_url = "https://other.atlassian.net/rest/api/3/issue"
        url = client._build_url(full_url)
        assert url == full_url
        client.close()

    def test_build_url_without_leading_slash(self):
        """Test URL building without leading slash."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        url = client._build_url("rest/api/3/myself")
        assert url == "https://example.atlassian.net/rest/api/3/myself"
        client.close()

    def test_context_manager(self):
        """Test context manager behavior."""
        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            assert not client._closed
        assert client._closed

    def test_close_session(self):
        """Test closing the session."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        assert not client._closed
        client.close()
        assert client._closed

    def test_close_twice_no_error(self):
        """Test closing twice doesn't raise error."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        client.close()
        client.close()  # Should not raise
        assert client._closed

    def test_request_after_close_raises_error(self):
        """Test that request after close raises error."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        client.close()
        with pytest.raises(JiraValidationError) as exc_info:
            client.get("/rest/api/3/myself")
        assert "closed" in str(exc_info.value).lower()

    @patch.object(requests.Session, 'request')
    def test_get_request(self, mock_request):
        """Test GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            response = client.get("/rest/api/3/myself", params={"expand": "groups"})

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["method"] == "GET"
        assert "myself" in call_kwargs[1]["url"]
        assert call_kwargs[1]["params"] == {"expand": "groups"}

    @patch.object(requests.Session, 'request')
    def test_post_request(self, mock_request):
        """Test POST request."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            response = client.post(
                "/rest/api/3/issue",
                json={"fields": {"summary": "Test"}}
            )

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["method"] == "POST"
        assert call_kwargs[1]["json"] == {"fields": {"summary": "Test"}}

    @patch.object(requests.Session, 'request')
    def test_put_request(self, mock_request):
        """Test PUT request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            response = client.put(
                "/rest/api/3/issue/TEST-1",
                json={"fields": {"summary": "Updated"}}
            )

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["method"] == "PUT"

    @patch.object(requests.Session, 'request')
    def test_delete_request(self, mock_request):
        """Test DELETE request."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            response = client.delete("/rest/api/3/issue/TEST-1")

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["method"] == "DELETE"

    @patch.object(requests.Session, 'request')
    def test_patch_request(self, mock_request):
        """Test PATCH request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            response = client.patch(
                "/rest/api/3/issue/TEST-1",
                json={"fields": {"summary": "Patched"}}
            )

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["method"] == "PATCH"

    @patch.object(requests.Session, 'request')
    def test_request_timeout(self, mock_request):
        """Test request timeout handling."""
        mock_request.side_effect = requests.exceptions.Timeout()

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            with pytest.raises(JiraAPIError) as exc_info:
                client.get("/rest/api/3/myself")
        assert "timed out" in str(exc_info.value).lower()

    @patch.object(requests.Session, 'request')
    def test_request_connection_error(self, mock_request):
        """Test request connection error handling."""
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            with pytest.raises(JiraAPIError) as exc_info:
                client.get("/rest/api/3/myself")
        assert "connection" in str(exc_info.value).lower()

    @patch.object(requests.Session, 'request')
    def test_custom_timeout(self, mock_request):
        """Test custom timeout in request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            client.get("/rest/api/3/myself", timeout=120)

        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["timeout"] == 120

    @patch.object(requests.Session, 'request')
    def test_custom_headers(self, mock_request):
        """Test custom headers in request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        with JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        ) as client:
            client.get(
                "/rest/api/3/myself",
                headers={"X-Custom-Header": "value"}
            )

        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["headers"] == {"X-Custom-Header": "value"}

    def test_default_headers_set(self):
        """Test that default headers are set."""
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="test@example.com",
            token="api-token",
        )
        assert client.session.headers["Content-Type"] == "application/json"
        assert client.session.headers["Accept"] == "application/json"
        client.close()


class TestCreatePooledSession:
    """Tests for create_pooled_session function."""

    def test_creates_session(self):
        """Test that function creates a session."""
        session = create_pooled_session()
        assert isinstance(session, requests.Session)
        session.close()

    def test_custom_pool_settings(self):
        """Test custom pool settings."""
        session = create_pooled_session(
            pool_connections=20,
            pool_maxsize=30,
            max_retries=5,
            backoff_factor=0.5,
        )
        assert isinstance(session, requests.Session)
        # Verify adapters are mounted
        assert "https://" in session.adapters
        assert "http://" in session.adapters
        session.close()

    def test_retry_adapter_mounted(self):
        """Test that retry adapter is mounted for both protocols."""
        session = create_pooled_session()
        https_adapter = session.get_adapter("https://example.com")
        http_adapter = session.get_adapter("http://example.com")
        assert https_adapter is not None
        assert http_adapter is not None
        session.close()
