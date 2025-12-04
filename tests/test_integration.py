#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Integration tests using HTTP mocking with the responses library.

These tests verify the behavior of jiraone components with mocked HTTP responses.
"""
import pytest
import responses

from jiraone.client import JiraClient, ClientConfig
from jiraone.exceptions import (
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraRateLimitError,
    raise_for_status,
)


class TestJiraClientIntegration:
    """Integration tests for JiraClient with mocked HTTP."""

    def test_get_myself_success(
        self, mock_jira_myself, base_url, user_email, api_token, sample_user_data
    ):
        """Test successful /myself API call."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get("/rest/api/3/myself")

        assert response.status_code == 200
        data = response.json()
        assert data["accountId"] == sample_user_data["accountId"]
        assert data["displayName"] == sample_user_data["displayName"]

    def test_get_project_success(
        self, mock_jira_project, base_url, user_email, api_token, project_key, sample_project_data
    ):
        """Test successful project retrieval."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(f"/rest/api/3/project/{project_key}")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == project_key
        assert data["name"] == sample_project_data["name"]

    def test_get_issue_success(
        self, mock_jira_issue, base_url, user_email, api_token, issue_key, sample_issue_data
    ):
        """Test successful issue retrieval."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(f"/rest/api/3/issue/{issue_key}")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == issue_key
        assert data["fields"]["summary"] == sample_issue_data["fields"]["summary"]

    def test_search_issues_get(
        self, mock_jira_search, base_url, user_email, api_token, sample_issues_list
    ):
        """Test JQL search using GET."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(
                "/rest/api/3/search",
                params={"jql": "project = TEST", "maxResults": 50}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["issues"]) == 1

    def test_search_issues_post(
        self, mock_jira_search, base_url, user_email, api_token, sample_issues_list
    ):
        """Test JQL search using POST."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.post(
                "/rest/api/3/search",
                json={"jql": "project = TEST", "maxResults": 50}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_get_fields(
        self, mock_jira_fields, base_url, user_email, api_token, sample_field_data
    ):
        """Test retrieving fields."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get("/rest/api/3/field")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_field_data["id"]


class TestErrorHandling:
    """Test error handling with mocked HTTP responses."""

    def test_unauthorized_raises_exception(
        self, mock_jira_unauthorized, base_url, user_email, api_token
    ):
        """Test that 401 responses raise JiraAuthenticationError."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get("/rest/api/3/myself")

        assert response.status_code == 401
        with pytest.raises(JiraAuthenticationError):
            raise_for_status(response)

    def test_not_found_raises_exception(
        self, mock_jira_not_found, base_url, user_email, api_token, issue_key
    ):
        """Test that 404 responses raise JiraNotFoundError."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(f"/rest/api/3/issue/{issue_key}")

        assert response.status_code == 404
        with pytest.raises(JiraNotFoundError):
            raise_for_status(response)

    def test_rate_limit_raises_exception(
        self, mock_jira_rate_limit, base_url, user_email, api_token
    ):
        """Test that 429 responses raise JiraRateLimitError."""
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get("/rest/api/3/myself")

        assert response.status_code == 429
        with pytest.raises(JiraRateLimitError) as exc_info:
            raise_for_status(response)
        assert exc_info.value.retry_after == 60


class TestCustomMocking:
    """Test using custom mocked responses."""

    def test_create_issue(self, mocked_responses, base_url, user_email, api_token, project_key):
        """Test creating an issue with mocked POST response."""
        new_issue = {
            "id": "10002",
            "key": f"{project_key}-124",
            "self": f"{base_url}/rest/api/3/issue/{project_key}-124",
        }
        mocked_responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue",
            json=new_issue,
            status=201,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.post(
                "/rest/api/3/issue",
                json={
                    "fields": {
                        "project": {"key": project_key},
                        "summary": "New test issue",
                        "issuetype": {"name": "Task"},
                    }
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["key"] == f"{project_key}-124"

    def test_update_issue(self, mocked_responses, base_url, user_email, api_token, issue_key):
        """Test updating an issue with mocked PUT response."""
        mocked_responses.add(
            responses.PUT,
            f"{base_url}/rest/api/3/issue/{issue_key}",
            status=204,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.put(
                f"/rest/api/3/issue/{issue_key}",
                json={"fields": {"summary": "Updated summary"}}
            )

        assert response.status_code == 204

    def test_delete_issue(self, mocked_responses, base_url, user_email, api_token, issue_key):
        """Test deleting an issue with mocked DELETE response."""
        mocked_responses.add(
            responses.DELETE,
            f"{base_url}/rest/api/3/issue/{issue_key}",
            status=204,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.delete(f"/rest/api/3/issue/{issue_key}")

        assert response.status_code == 204

    def test_add_comment(self, mocked_responses, base_url, user_email, api_token, issue_key):
        """Test adding a comment with mocked POST response."""
        comment_response = {
            "id": "10001",
            "body": "Test comment",
            "author": {"displayName": "Test User"},
        }
        mocked_responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue/{issue_key}/comment",
            json=comment_response,
            status=201,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.post(
                f"/rest/api/3/issue/{issue_key}/comment",
                json={"body": "Test comment"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["body"] == "Test comment"


class TestOAuthAuthentication:
    """Test OAuth authentication with mocked responses."""

    def test_oauth_bearer_token(self, mocked_responses, base_url, oauth_token, sample_user_data):
        """Test that OAuth bearer token is used correctly."""
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json=sample_user_data,
            status=200,
        )

        with JiraClient(base_url=base_url, oauth_token=oauth_token) as client:
            response = client.get("/rest/api/3/myself")

        assert response.status_code == 200
        # Verify the Authorization header was set
        assert len(mocked_responses.calls) == 1
        auth_header = mocked_responses.calls[0].request.headers.get("Authorization")
        assert auth_header == f"Bearer {oauth_token}"


class TestPagination:
    """Test pagination with mocked responses."""

    def test_paginated_search(self, mocked_responses, base_url, user_email, api_token, project_key):
        """Test iterating through paginated search results."""
        # First page
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search",
            json={
                "startAt": 0,
                "maxResults": 2,
                "total": 5,
                "issues": [
                    {"key": f"{project_key}-1"},
                    {"key": f"{project_key}-2"},
                ]
            },
            status=200,
        )
        # Second page
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search",
            json={
                "startAt": 2,
                "maxResults": 2,
                "total": 5,
                "issues": [
                    {"key": f"{project_key}-3"},
                    {"key": f"{project_key}-4"},
                ]
            },
            status=200,
        )
        # Third page (last)
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/search",
            json={
                "startAt": 4,
                "maxResults": 2,
                "total": 5,
                "issues": [
                    {"key": f"{project_key}-5"},
                ]
            },
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            # Fetch first page
            response1 = client.get("/rest/api/3/search", params={"startAt": 0, "maxResults": 2})
            assert response1.status_code == 200
            data1 = response1.json()
            assert len(data1["issues"]) == 2

            # Fetch second page
            response2 = client.get("/rest/api/3/search", params={"startAt": 2, "maxResults": 2})
            assert response2.status_code == 200
            data2 = response2.json()
            assert len(data2["issues"]) == 2

            # Fetch third page
            response3 = client.get("/rest/api/3/search", params={"startAt": 4, "maxResults": 2})
            assert response3.status_code == 200
            data3 = response3.json()
            assert len(data3["issues"]) == 1

        # Total of 5 issues across 3 pages
        assert len(mocked_responses.calls) == 3
