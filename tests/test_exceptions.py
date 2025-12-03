#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for jiraone.exceptions module."""
import pytest
import sys
sys.path.insert(0, 'src')

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


class TestJiraOneErrors:
    """Tests for the base JiraOneErrors exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        exc = JiraOneErrors("value", "Test message")
        assert exc.errors == "value"
        assert exc.messages == "Test message"

    def test_str_with_name_error(self):
        """Test string representation for name errors."""
        exc = JiraOneErrors("name", "Field not found")
        assert "Field not found" in str(exc)

    def test_str_with_value_error(self):
        """Test string representation for value errors."""
        exc = JiraOneErrors("value", "Invalid value")
        assert "Invalid value" in str(exc)

    def test_str_with_login_error(self):
        """Test string representation for login errors."""
        exc = JiraOneErrors("login", "Login failed")
        assert "Login failed" in str(exc)

    def test_default_message(self):
        """Test that default message is used when none provided."""
        exc = JiraOneErrors("wrong")
        assert "incorrect" in str(exc).lower() or str(exc)


class TestJiraAuthenticationError:
    """Tests for JiraAuthenticationError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraAuthenticationError()
        assert "Authentication failed" in str(exc)

    def test_with_status_code(self):
        """Test with status code."""
        exc = JiraAuthenticationError(
            message="Invalid token",
            status_code=401
        )
        assert "401" in str(exc)
        assert "Invalid token" in str(exc)

    def test_inheritance(self):
        """Test that it inherits from JiraOneErrors."""
        exc = JiraAuthenticationError()
        assert isinstance(exc, JiraOneErrors)
        assert exc.errors == "login"


class TestJiraAPIError:
    """Tests for JiraAPIError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraAPIError(
            message="Server error",
            status_code=500
        )
        assert exc.status_code == 500
        assert "Server error" in str(exc)

    def test_with_url_and_method(self):
        """Test with URL and method."""
        exc = JiraAPIError(
            message="Not found",
            status_code=404,
            url="https://example.com/api/issue",
            method="GET"
        )
        assert "GET" in str(exc)
        assert "404" in str(exc)

    def test_from_response(self):
        """Test creating from a mock response."""
        class MockResponse:
            status_code = 400
            url = "https://example.com/api"
            text = '{"errorMessages": ["Bad request"]}'

            class request:
                method = "POST"

            def json(self):
                return {"errorMessages": ["Bad request"]}

        exc = JiraAPIError.from_response(MockResponse())
        assert exc.status_code == 400
        assert "Bad request" in str(exc)


class TestJiraRateLimitError:
    """Tests for JiraRateLimitError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraRateLimitError()
        assert exc.status_code == 429
        assert "Rate limit" in str(exc)

    def test_with_retry_after(self):
        """Test with retry_after value."""
        exc = JiraRateLimitError(retry_after=60)
        assert exc.retry_after == 60
        assert "60s" in str(exc)

    def test_inheritance(self):
        """Test inheritance from JiraAPIError."""
        exc = JiraRateLimitError()
        assert isinstance(exc, JiraAPIError)


class TestJiraNotFoundError:
    """Tests for JiraNotFoundError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraNotFoundError()
        assert exc.status_code == 404

    def test_with_resource_info(self):
        """Test with resource type and ID."""
        exc = JiraNotFoundError(
            resource_type="issue",
            resource_id="TEST-123"
        )
        assert "issue" in str(exc)
        assert "TEST-123" in str(exc)


class TestJiraPermissionError:
    """Tests for JiraPermissionError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraPermissionError()
        assert exc.status_code == 403

    def test_with_required_permission(self):
        """Test with required permission info."""
        exc = JiraPermissionError(
            message="Access denied",
            required_permission="ADMINISTER_PROJECTS"
        )
        assert "ADMINISTER_PROJECTS" in str(exc)


class TestJiraValidationError:
    """Tests for JiraValidationError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraValidationError(message="Invalid input")
        assert "Invalid input" in str(exc)

    def test_with_field_info(self):
        """Test with field information."""
        exc = JiraValidationError(
            message="Value too long",
            field="summary",
            value="x" * 300
        )
        assert "summary" in str(exc)

    def test_inheritance(self):
        """Test inheritance from JiraOneErrors."""
        exc = JiraValidationError()
        assert isinstance(exc, JiraOneErrors)
        assert exc.errors == "value"


class TestJiraFieldError:
    """Tests for JiraFieldError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraFieldError(message="Field not found")
        assert "Field not found" in str(exc)

    def test_with_field_name(self):
        """Test with field name."""
        exc = JiraFieldError(
            message="Cannot update",
            field_name="Custom Field 1"
        )
        assert "Custom Field 1" in str(exc)


class TestJiraUserError:
    """Tests for JiraUserError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraUserError(message="User not found")
        assert "User not found" in str(exc)

    def test_with_email(self):
        """Test with email."""
        exc = JiraUserError(
            message="Invalid user",
            email="test@example.com"
        )
        assert "test@example.com" in str(exc)


class TestJiraFileError:
    """Tests for JiraFileError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraFileError(message="Upload failed")
        assert "Upload failed" in str(exc)

    def test_with_filename_and_operation(self):
        """Test with filename and operation."""
        exc = JiraFileError(
            message="Failed",
            filename="document.pdf",
            operation="download"
        )
        assert "document.pdf" in str(exc)
        assert "download" in str(exc)


class TestJiraTimeoutError:
    """Tests for JiraTimeoutError."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        exc = JiraTimeoutError()
        assert "timeout" in str(exc).lower()

    def test_with_timeout_value(self):
        """Test with timeout value."""
        exc = JiraTimeoutError(timeout=30.0)
        assert "30" in str(exc)


class TestRaiseForStatus:
    """Tests for raise_for_status function."""

    def test_no_error_on_success(self):
        """Test that no error is raised for success status codes."""
        class MockResponse:
            status_code = 200

        # Should not raise
        raise_for_status(MockResponse())

    def test_raises_rate_limit_error(self):
        """Test that 429 raises JiraRateLimitError."""
        class MockResponse:
            status_code = 429
            headers = {"Retry-After": "60"}

        with pytest.raises(JiraRateLimitError) as exc_info:
            raise_for_status(MockResponse())
        assert exc_info.value.retry_after == 60

    def test_raises_auth_error(self):
        """Test that 401 raises JiraAuthenticationError."""
        class MockResponse:
            status_code = 401

        with pytest.raises(JiraAuthenticationError):
            raise_for_status(MockResponse())

    def test_raises_permission_error(self):
        """Test that 403 raises JiraPermissionError."""
        class MockResponse:
            status_code = 403
            url = "https://example.com"
            text = "{}"
            class request:
                method = "GET"
            def json(self):
                return {}

        with pytest.raises(JiraPermissionError):
            raise_for_status(MockResponse())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
