#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the credentials module."""
import pytest
from unittest.mock import Mock, patch
import requests

from jiraone.credentials import Credentials, InitProcess, LOGIN


class TestCredentials:
    """Tests for Credentials class."""

    def test_init_without_auth(self):
        """Test initialization without authentication."""
        cred = Credentials()
        assert cred.auth_request is None
        assert cred.base_url is None
        assert cred.session is not None

    def test_init_with_basic_auth(self):
        """Test initialization with basic auth."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        assert cred.auth_request is not None
        assert cred.base_url == "https://example.atlassian.net"
        assert cred.headers is not None

    def test_init_with_existing_session(self):
        """Test initialization with existing session."""
        existing_session = requests.Session()
        cred = Credentials(session=existing_session)
        assert cred.session is existing_session
        existing_session.close()

    def test_token_session_basic_auth(self):
        """Test token_session with basic auth."""
        cred = Credentials()
        cred.token_session(email="test@example.com", token="api-token")
        assert cred.auth_request is not None
        assert cred.headers == {"Content-Type": "application/json"}


class TestCredentialsContextManager:
    """Tests for Credentials context manager functionality."""

    def test_session_context_creates_session(self):
        """Test that session_context creates a session."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred.session_context() as session:
            assert isinstance(session, requests.Session)
            assert session.auth is not None

    def test_session_context_closes_session(self):
        """Test that session_context closes session on exit."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred.session_context() as session:
            pass
        # Session should be closed after exiting context
        # We can't directly check if closed, but we can verify it ran

    def test_session_context_with_custom_pool_settings(self):
        """Test session_context with custom pool settings."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred.session_context(
            pool_connections=20,
            pool_maxsize=30,
            max_retries=5,
        ) as session:
            assert isinstance(session, requests.Session)
            # Verify adapters are mounted
            assert "https://" in session.adapters
            assert "http://" in session.adapters

    def test_session_context_applies_auth(self):
        """Test that session_context applies authentication."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred.session_context() as session:
            assert session.auth is not None

    def test_session_context_applies_headers(self):
        """Test that session_context applies headers."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred.session_context() as session:
            assert "Content-Type" in session.headers

    def test_credentials_as_context_manager(self):
        """Test using Credentials directly as context manager."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        with cred as c:
            assert c is cred

    def test_close_method(self):
        """Test the close method."""
        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        # Should not raise
        cred.close()

    def test_close_without_session(self):
        """Test close when session is None."""
        cred = Credentials()
        cred.session = None
        # Should not raise
        cred.close()


class TestInitProcess:
    """Tests for InitProcess class."""

    def test_callable(self):
        """Test that InitProcess is callable."""
        init = InitProcess()
        # Should be callable
        init(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        assert init.base_url == "https://example.atlassian.net"

    def test_inherits_from_credentials(self):
        """Test that InitProcess inherits from Credentials."""
        assert issubclass(InitProcess, Credentials)


class TestLOGIN:
    """Tests for the global LOGIN instance."""

    def test_login_is_init_process(self):
        """Test that LOGIN is an InitProcess instance."""
        assert isinstance(LOGIN, InitProcess)

    def test_login_has_session_context(self):
        """Test that LOGIN has session_context method."""
        assert hasattr(LOGIN, 'session_context')
        assert callable(LOGIN.session_context)

    def test_login_has_close(self):
        """Test that LOGIN has close method."""
        assert hasattr(LOGIN, 'close')
        assert callable(LOGIN.close)

    def test_login_context_manager(self):
        """Test that LOGIN can be used as context manager."""
        # Should not raise
        with LOGIN:
            pass


class TestCredentialsHTTPMethods:
    """Tests for HTTP methods in Credentials class."""

    @patch('requests.get')
    def test_get_method(self, mock_get):
        """Test GET request method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        response = cred.get("https://example.atlassian.net/rest/api/3/myself")

        mock_get.assert_called_once()
        assert response.status_code == 200

    @patch('requests.post')
    def test_post_method(self, mock_post):
        """Test POST request method."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        response = cred.post(
            "https://example.atlassian.net/rest/api/3/issue",
            payload={"fields": {"summary": "Test"}}
        )

        mock_post.assert_called_once()
        assert response.status_code == 201

    @patch('requests.put')
    def test_put_method(self, mock_put):
        """Test PUT request method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        response = cred.put(
            "https://example.atlassian.net/rest/api/3/issue/TEST-1",
            payload={"fields": {"summary": "Updated"}}
        )

        mock_put.assert_called_once()
        assert response.status_code == 200

    @patch('requests.delete')
    def test_delete_method(self, mock_delete):
        """Test DELETE request method."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        response = cred.delete(
            "https://example.atlassian.net/rest/api/3/issue/TEST-1"
        )

        mock_delete.assert_called_once()
        assert response.status_code == 204

    @patch('requests.request')
    def test_custom_method(self, mock_request):
        """Test custom_method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        cred = Credentials(
            user="test@example.com",
            password="api-token",
            url="https://example.atlassian.net",
        )
        response = cred.custom_method(
            "PATCH",
            "https://example.atlassian.net/rest/api/3/issue/TEST-1",
            json={"fields": {"summary": "Patched"}}
        )

        mock_request.assert_called_once()
        assert response.status_code == 200
