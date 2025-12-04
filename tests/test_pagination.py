#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for jiraone.pagination module."""
import pytest
import sys
sys.path.insert(0, 'src')

from jiraone.pagination import (
    PaginatedAPI,
    SearchResultsIterator,
    paginate,
)


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.headers = {}

    def json(self):
        return self._data


class MockClient:
    """Mock client that returns paginated data."""

    def __init__(self, pages):
        """Initialize with list of pages to return."""
        self.pages = pages
        self.call_count = 0

    def get(self, url):
        if self.call_count >= len(self.pages):
            return MockResponse({"values": [], "total": 0})
        response = MockResponse(self.pages[self.call_count])
        self.call_count += 1
        return response


class TestPaginatedAPI:
    """Tests for PaginatedAPI iterator."""

    def test_single_page(self):
        """Test iteration over single page of results."""
        client = MockClient([
            {"values": [{"id": 1}, {"id": 2}, {"id": 3}], "total": 3}
        ])

        def endpoint_func(start_at=0, max_results=50):
            return f"https://example.com/api?startAt={start_at}&maxResults={max_results}"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
            results_key="values",
            total_key="total",
        )

        results = list(paginator)
        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[2]["id"] == 3

    def test_multiple_pages(self):
        """Test iteration over multiple pages."""
        client = MockClient([
            {"values": [{"id": 1}, {"id": 2}], "total": 5},
            {"values": [{"id": 3}, {"id": 4}], "total": 5},
            {"values": [{"id": 5}], "total": 5},
        ])

        def endpoint_func(start_at=0, max_results=50):
            return f"https://example.com/api?startAt={start_at}"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
            max_results=2,
        )

        results = list(paginator)
        assert len(results) == 5
        assert [r["id"] for r in results] == [1, 2, 3, 4, 5]

    def test_empty_results(self):
        """Test handling of empty results."""
        client = MockClient([
            {"values": [], "total": 0}
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
        )

        results = list(paginator)
        assert len(results) == 0

    def test_total_property(self):
        """Test total property."""
        client = MockClient([
            {"values": [{"id": 1}], "total": 100}
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
        )

        # Total is None before first fetch
        assert paginator.total is None

        # Iterate to trigger fetch
        next(iter(paginator))

        # Total should now be set
        assert paginator.total == 100

    def test_pages_method(self):
        """Test pages() method for batch iteration."""
        client = MockClient([
            {"values": [{"id": 1}, {"id": 2}], "total": 4},
            {"values": [{"id": 3}, {"id": 4}], "total": 4},
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
            max_results=2,
        )

        pages = list(paginator.pages())
        assert len(pages) == 2
        assert len(pages[0]) == 2
        assert len(pages[1]) == 2

    def test_collect_method(self):
        """Test collect() method."""
        client = MockClient([
            {"values": [{"id": 1}, {"id": 2}], "total": 3},
            {"values": [{"id": 3}], "total": 3},
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
        )

        results = paginator.collect()
        assert len(results) == 3

    def test_collect_with_max_items(self):
        """Test collect() with max_items limit."""
        client = MockClient([
            {"values": [{"id": i} for i in range(1, 11)], "total": 10}
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
        )

        results = paginator.collect(max_items=5)
        assert len(results) == 5

    def test_reset(self):
        """Test reset() method."""
        client = MockClient([
            {"values": [{"id": 1}], "total": 1},
            {"values": [{"id": 1}], "total": 1},  # Second iteration
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        paginator = PaginatedAPI(
            client=client,
            endpoint_func=endpoint_func,
        )

        # First iteration
        results1 = list(paginator)
        assert len(results1) == 1

        # Reset and iterate again
        paginator.reset()
        results2 = list(paginator)
        assert len(results2) == 1


class TestSearchResultsIterator:
    """Tests for SearchResultsIterator."""

    def test_basic_search(self):
        """Test basic JQL search iteration."""
        class SearchMockClient:
            def __init__(self):
                self.call_count = 0

            def get(self, url):
                self.call_count += 1
                if self.call_count == 1:
                    return MockResponse({
                        "issues": [
                            {"key": "TEST-1", "fields": {"summary": "Issue 1"}},
                            {"key": "TEST-2", "fields": {"summary": "Issue 2"}},
                        ],
                        "total": 2
                    })
                return MockResponse({"issues": [], "total": 2})

        client = SearchMockClient()
        iterator = SearchResultsIterator(
            client=client,
            jql="project = TEST",
        )

        results = list(iterator)
        assert len(results) == 2
        assert results[0]["key"] == "TEST-1"

    def test_total_property(self):
        """Test total property for search results."""
        class SearchMockClient:
            def get(self, url):
                return MockResponse({"issues": [], "total": 42})

        iterator = SearchResultsIterator(
            client=SearchMockClient(),
            jql="project = TEST",
        )

        # Trigger fetch
        list(iterator)
        assert iterator.total == 42


class TestPaginateFunction:
    """Tests for paginate() convenience function."""

    def test_basic_usage(self):
        """Test basic paginate function usage."""
        client = MockClient([
            {"values": [{"id": 1}, {"id": 2}], "total": 2}
        ])

        def endpoint_func(**kwargs):
            return "https://example.com/api"

        results = list(paginate(client, endpoint_func))
        assert len(results) == 2

    def test_with_kwargs(self):
        """Test paginate with additional kwargs."""
        received_kwargs = {}

        def endpoint_func(**kwargs):
            received_kwargs.update(kwargs)
            return "https://example.com/api"

        client = MockClient([
            {"values": [], "total": 0}
        ])

        list(paginate(
            client,
            endpoint_func,
            custom_param="value"
        ))

        assert "custom_param" in received_kwargs
        assert received_kwargs["custom_param"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
