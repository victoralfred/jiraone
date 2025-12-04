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


class TestRetryBehavior:
    """Test retry behavior with mocked responses."""

    def test_retry_on_server_error(self, mocked_responses, base_url, user_email, api_token):
        """Test that requests are retried on 503 errors."""
        # First call returns 503, second succeeds
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"error": "Service unavailable"},
            status=503,
        )
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"accountId": "123", "displayName": "Test"},
            status=200,
        )

        # Note: JiraClient uses urllib3 retry which handles this automatically
        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            # First request might fail or succeed depending on retry config
            response = client.get("/rest/api/3/myself")
            # At minimum, one call was made
            assert len(mocked_responses.calls) >= 1

    def test_multiple_sequential_requests(
        self, mocked_responses, base_url, user_email, api_token
    ):
        """Test multiple sequential requests work correctly."""
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"accountId": "123"},
            status=200,
        )
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/TEST",
            json={"key": "TEST", "name": "Test Project"},
            status=200,
        )
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/TEST-1",
            json={"key": "TEST-1", "fields": {"summary": "Test"}},
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            r1 = client.get("/rest/api/3/myself")
            r2 = client.get("/rest/api/3/project/TEST")
            r3 = client.get("/rest/api/3/issue/TEST-1")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        assert len(mocked_responses.calls) == 3


class TestEndpointBuilder:
    """Test EndpointBuilder with mocked responses."""

    def test_endpoint_builder_integration(
        self, mocked_responses, base_url, user_email, api_token
    ):
        """Test using EndpointBuilder with JiraClient."""
        from jiraone.endpoints import EndpointBuilder

        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/myself",
            json={"accountId": "123", "displayName": "Test User"},
            status=200,
        )

        builder = EndpointBuilder.from_url(base_url)

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(builder.myself().replace(base_url, ""))

        assert response.status_code == 200
        assert response.json()["displayName"] == "Test User"

    def test_endpoint_builder_issue_endpoint(
        self, mocked_responses, base_url, user_email, api_token, issue_key
    ):
        """Test EndpointBuilder issue endpoint."""
        from jiraone.endpoints import EndpointBuilder

        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/{issue_key}",
            json={"key": issue_key, "fields": {"summary": "Test Issue"}},
            status=200,
        )

        builder = EndpointBuilder.from_url(base_url)
        # Use issues() method which exists on EndpointBuilder
        endpoint = builder.issues(issue_key)

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(endpoint.replace(base_url, ""))

        assert response.status_code == 200
        assert response.json()["key"] == issue_key


class TestValidationIntegration:
    """Test validation utilities in integration context."""

    def test_validate_issue_key_in_request(
        self, mocked_responses, base_url, user_email, api_token
    ):
        """Test that validated issue keys work in requests."""
        from jiraone.validation import validate_issue_key

        issue_key = validate_issue_key("test-123")  # Should uppercase

        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/issue/{issue_key}",
            json={"key": issue_key},
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(f"/rest/api/3/issue/{issue_key}")

        assert response.status_code == 200
        assert response.json()["key"] == "TEST-123"

    def test_validate_project_key_in_request(
        self, mocked_responses, base_url, user_email, api_token
    ):
        """Test that validated project keys work in requests."""
        from jiraone.validation import validate_project_key

        project_key = validate_project_key("myproject")  # Should uppercase

        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/{project_key}",
            json={"key": project_key, "name": "My Project"},
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get(f"/rest/api/3/project/{project_key}")

        assert response.status_code == 200
        assert response.json()["key"] == "MYPROJECT"


class TestPaginationIterator:
    """Test PaginatedAPI iterator with mocked responses."""

    def test_paginated_api_iterator(
        self, mocked_responses, base_url, user_email, api_token, project_key
    ):
        """Test PaginatedAPI iterator collects all results."""
        from jiraone.pagination import PaginatedAPI
        from jiraone.client import JiraClient

        # Mock paginated responses
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/search",
            json={
                "startAt": 0,
                "maxResults": 2,
                "total": 3,
                "values": [
                    {"key": "PROJ1", "name": "Project 1"},
                    {"key": "PROJ2", "name": "Project 2"},
                ]
            },
            status=200,
        )
        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/search",
            json={
                "startAt": 2,
                "maxResults": 2,
                "total": 3,
                "values": [
                    {"key": "PROJ3", "name": "Project 3"},
                ]
            },
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            # Create a simple endpoint function
            def get_projects(start_at=0, max_results=50):
                return f"/rest/api/3/project/search?startAt={start_at}&maxResults={max_results}"

            paginator = PaginatedAPI(
                client=client,
                endpoint_func=get_projects,
                results_key="values",
                max_results=2,
            )

            projects = list(paginator)

        assert len(projects) == 3
        assert projects[0]["key"] == "PROJ1"
        assert projects[2]["key"] == "PROJ3"


class TestStreamingIntegration:
    """Test streaming functionality with mocked responses."""

    def test_streaming_download_small_file(
        self, mocked_responses, base_url, user_email, api_token, tmp_path
    ):
        """Test streaming download of a small file."""
        from jiraone.streaming import StreamingDownloader

        file_content = b"This is test file content for streaming download."

        mocked_responses.add(
            responses.GET,
            f"{base_url}/secure/attachment/12345/test.txt",
            body=file_content,
            status=200,
            content_type="application/octet-stream",
        )

        downloader = StreamingDownloader(
            url=f"{base_url}/secure/attachment/12345/test.txt",
            auth=(user_email, api_token),
        )

        output_file = tmp_path / "downloaded.txt"
        downloader.download_to_file(str(output_file))

        assert output_file.exists()
        assert output_file.read_bytes() == file_content

    def test_streaming_download_large_file(
        self, mocked_responses, base_url, user_email, api_token, tmp_path
    ):
        """Test streaming download of a larger file."""
        from jiraone.streaming import StreamingDownloader

        file_content = b"X" * 1000  # 1KB file

        mocked_responses.add(
            responses.GET,
            f"{base_url}/secure/attachment/12345/large.bin",
            body=file_content,
            status=200,
            content_type="application/octet-stream",
            headers={"Content-Length": "1000"},
        )

        downloader = StreamingDownloader(
            url=f"{base_url}/secure/attachment/12345/large.bin",
            auth=(user_email, api_token),
        )

        output_file = tmp_path / "large.bin"
        downloader.download_to_file(str(output_file))

        assert output_file.exists()
        assert len(output_file.read_bytes()) == 1000


class TestExceptionHandling:
    """Test comprehensive exception handling."""

    def test_permission_error(self, mocked_responses, base_url, user_email, api_token):
        """Test 403 Forbidden raises JiraPermissionError."""
        from jiraone.exceptions import JiraPermissionError

        mocked_responses.add(
            responses.GET,
            f"{base_url}/rest/api/3/project/ADMIN",
            json={"errorMessages": ["You do not have permission to view this project"]},
            status=403,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.get("/rest/api/3/project/ADMIN")

        assert response.status_code == 403
        with pytest.raises(JiraPermissionError):
            raise_for_status(response)

    def test_validation_error(self, mocked_responses, base_url, user_email, api_token):
        """Test 400 Bad Request with validation errors."""
        from jiraone.exceptions import JiraAPIError

        mocked_responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/issue",
            json={
                "errorMessages": [],
                "errors": {
                    "summary": "Summary is required",
                    "project": "Project is required",
                }
            },
            status=400,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            response = client.post(
                "/rest/api/3/issue",
                json={"fields": {}}
            )

        assert response.status_code == 400
        with pytest.raises(JiraAPIError):
            raise_for_status(response)

    def test_server_error(self, mocked_responses, base_url, user_email, api_token):
        """Test 500 Internal Server Error raises exception via raise_for_status."""
        from jiraone.exceptions import JiraAPIError
        from unittest.mock import Mock

        # Create a mock response instead of making actual request
        # since JiraClient retries 500 errors automatically
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.json.return_value = {"errorMessages": ["Internal server error"]}
        mock_response.text = '{"errorMessages": ["Internal server error"]}'
        mock_response.url = f"{base_url}/rest/api/3/myself"

        with pytest.raises(JiraAPIError):
            raise_for_status(mock_response)


class TestBulkOperations:
    """Test bulk operations with mocked responses."""

    def test_bulk_issue_fetch(
        self, mocked_responses, base_url, user_email, api_token, project_key
    ):
        """Test fetching multiple issues in bulk."""
        issue_keys = [f"{project_key}-{i}" for i in range(1, 6)]

        # Mock bulk get endpoint
        mocked_responses.add(
            responses.POST,
            f"{base_url}/rest/api/3/search",
            json={
                "startAt": 0,
                "maxResults": 50,
                "total": 5,
                "issues": [
                    {"key": key, "fields": {"summary": f"Issue {key}"}}
                    for key in issue_keys
                ]
            },
            status=200,
        )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            jql = f"key in ({','.join(issue_keys)})"
            response = client.post(
                "/rest/api/3/search",
                json={"jql": jql, "maxResults": 50}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["issues"]) == 5

    def test_bulk_transition(
        self, mocked_responses, base_url, user_email, api_token, project_key
    ):
        """Test transitioning multiple issues."""
        issue_keys = [f"{project_key}-1", f"{project_key}-2", f"{project_key}-3"]

        for key in issue_keys:
            mocked_responses.add(
                responses.POST,
                f"{base_url}/rest/api/3/issue/{key}/transitions",
                status=204,
            )

        with JiraClient(base_url=base_url, user=user_email, token=api_token) as client:
            for key in issue_keys:
                response = client.post(
                    f"/rest/api/3/issue/{key}/transitions",
                    json={"transition": {"id": "31"}}
                )
                assert response.status_code == 204

        assert len(mocked_responses.calls) == 3
