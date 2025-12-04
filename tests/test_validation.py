#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for jiraone.validation module."""
import pytest
import sys
sys.path.insert(0, 'src')

from jiraone.validation import (
    validate_url,
    sanitize_path_component,
    validate_issue_key,
    validate_project_key,
    validate_account_id,
    validate_jql,
    safe_format_url,
)
from jiraone.exceptions import JiraValidationError


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = validate_url("https://example.atlassian.net")
        assert url == "https://example.atlassian.net"

    def test_removes_trailing_slash(self):
        """Test that trailing slash is removed."""
        url = validate_url("https://example.atlassian.net/")
        assert not url.endswith("/")

    def test_adds_https_if_missing(self):
        """Test that HTTPS is added if no scheme."""
        url = validate_url("example.atlassian.net", require_https=False)
        assert url.startswith("https://")

    def test_empty_url_raises_error(self):
        """Test that empty URL raises error."""
        with pytest.raises(JiraValidationError):
            validate_url("")

    def test_http_raises_error_when_https_required(self):
        """Test that HTTP raises error when HTTPS is required."""
        with pytest.raises(JiraValidationError) as exc_info:
            validate_url("http://example.com", require_https=True)
        assert "HTTPS is required" in str(exc_info.value)

    def test_http_allowed_when_not_required(self):
        """Test that HTTP is allowed when not required."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            url = validate_url("http://localhost:8080", require_https=False, warn_http=False)
        assert url == "http://localhost:8080"

    def test_allowed_hosts(self):
        """Test allowed hosts restriction."""
        url = validate_url(
            "https://mycompany.atlassian.net",
            allowed_hosts=["mycompany.atlassian.net"]
        )
        assert url == "https://mycompany.atlassian.net"

    def test_disallowed_host_raises_error(self):
        """Test that disallowed host raises error."""
        with pytest.raises(JiraValidationError) as exc_info:
            validate_url(
                "https://other.atlassian.net",
                allowed_hosts=["mycompany.atlassian.net"]
            )
        assert "not in allowed hosts" in str(exc_info.value)

    def test_invalid_scheme_raises_error(self):
        """Test that invalid scheme raises error."""
        with pytest.raises(JiraValidationError):
            validate_url("ftp://example.com")


class TestSanitizePathComponent:
    """Tests for sanitize_path_component function."""

    def test_basic_sanitization(self):
        """Test basic path sanitization."""
        result = sanitize_path_component("PROJECT-123")
        assert result == "PROJECT-123"

    def test_removes_unsafe_characters(self):
        """Test that unsafe characters are removed."""
        result = sanitize_path_component("test<script>")
        assert "<" not in result
        assert ">" not in result

    def test_empty_raises_error(self):
        """Test that empty value raises error."""
        with pytest.raises(JiraValidationError):
            sanitize_path_component("")

    def test_max_length_enforcement(self):
        """Test that max length is enforced."""
        with pytest.raises(JiraValidationError):
            sanitize_path_component("x" * 300, max_length=256)

    def test_allows_slashes_when_enabled(self):
        """Test that slashes are allowed when enabled."""
        result = sanitize_path_component("issues/attachments", allow_slashes=True)
        assert "/" in result


class TestValidateIssueKey:
    """Tests for validate_issue_key function."""

    def test_valid_issue_key(self):
        """Test valid issue key."""
        key = validate_issue_key("PROJECT-123")
        assert key == "PROJECT-123"

    def test_lowercase_is_uppercased(self):
        """Test that lowercase is converted to uppercase."""
        key = validate_issue_key("test-456")
        assert key == "TEST-456"

    def test_empty_raises_error(self):
        """Test that empty key raises error."""
        with pytest.raises(JiraValidationError):
            validate_issue_key("")

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises error."""
        with pytest.raises(JiraValidationError) as exc_info:
            validate_issue_key("invalid")
        assert "format" in str(exc_info.value).lower()

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        key = validate_issue_key("  TEST-789  ")
        assert key == "TEST-789"


class TestValidateProjectKey:
    """Tests for validate_project_key function."""

    def test_valid_project_key(self):
        """Test valid project key."""
        key = validate_project_key("PROJECT")
        assert key == "PROJECT"

    def test_lowercase_is_uppercased(self):
        """Test that lowercase is converted to uppercase."""
        key = validate_project_key("myproject")
        assert key == "MYPROJECT"

    def test_empty_raises_error(self):
        """Test that empty key raises error."""
        with pytest.raises(JiraValidationError):
            validate_project_key("")

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises error."""
        with pytest.raises(JiraValidationError):
            validate_project_key("123PROJECT")  # Can't start with number

    def test_with_numbers_and_underscore(self):
        """Test key with numbers and underscore."""
        key = validate_project_key("TEST_PROJECT1")
        assert key == "TEST_PROJECT1"


class TestValidateAccountId:
    """Tests for validate_account_id function."""

    def test_valid_account_id(self):
        """Test valid account ID."""
        aid = validate_account_id("557058:12345678-1234-1234-1234-123456789012")
        assert aid == "557058:12345678-1234-1234-1234-123456789012"

    def test_empty_raises_error(self):
        """Test that empty ID raises error."""
        with pytest.raises(JiraValidationError):
            validate_account_id("")

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        aid = validate_account_id("  abc123  ")
        assert aid == "abc123"


class TestValidateJql:
    """Tests for validate_jql function."""

    def test_valid_jql(self):
        """Test valid JQL."""
        jql = validate_jql("project = TEST ORDER BY created DESC")
        assert jql == "project = TEST ORDER BY created DESC"

    def test_empty_raises_error(self):
        """Test that empty JQL raises error."""
        with pytest.raises(JiraValidationError):
            validate_jql("")

    def test_max_length_enforcement(self):
        """Test that max length is enforced."""
        with pytest.raises(JiraValidationError):
            validate_jql("x" * 11000, max_length=10000)

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        jql = validate_jql("  project = TEST  ")
        assert jql == "project = TEST"


class TestSafeFormatUrl:
    """Tests for safe_format_url function."""

    def test_basic_formatting(self):
        """Test basic URL formatting."""
        url = safe_format_url(
            "https://example.atlassian.net",
            "/rest/api/3/issue/{key}",
            key="PROJECT-123"
        )
        assert url == "https://example.atlassian.net/rest/api/3/issue/PROJECT-123"

    def test_integer_parameters(self):
        """Test formatting with integer parameters."""
        url = safe_format_url(
            "https://example.atlassian.net",
            "/rest/api/3/project/{id}",
            id=12345
        )
        assert "12345" in url

    def test_missing_parameter_raises_error(self):
        """Test that missing parameter raises error."""
        with pytest.raises(JiraValidationError):
            safe_format_url(
                "https://example.atlassian.net",
                "/rest/api/3/issue/{key}",
                # key is missing
            )

    def test_sanitizes_parameters(self):
        """Test that parameters are sanitized."""
        url = safe_format_url(
            "https://example.atlassian.net",
            "/rest/api/3/search/{query}",
            query="test<script>"
        )
        assert "<" not in url
        assert ">" not in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
