#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pagination utilities for Jira API requests.

This module provides iterator classes for handling paginated API responses
in a memory-efficient way.

Example::

    from jiraone import LOGIN, endpoint
    from jiraone.pagination import PaginatedAPI

    # Iterate through all projects
    for project in PaginatedAPI(
        client=LOGIN,
        endpoint_func=endpoint.get_projects,
        results_key="values"
    ):
        print(project["name"])

    # Or collect all at once (use with caution for large datasets)
    all_projects = list(PaginatedAPI(
        client=LOGIN,
        endpoint_func=endpoint.get_projects,
        results_key="values"
    ))
"""
import time
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Union


class PaginatedAPI:
    """Iterator for paginated Jira API responses.

    This class handles the common pagination pattern used by Jira APIs,
    automatically fetching subsequent pages as needed.

    Attributes:
        client: The authenticated client (LOGIN instance).
        endpoint_func: Function that generates the endpoint URL.
        results_key: Key in the response that contains the results array.
        total_key: Key in the response that contains total count.
        start_key: Query parameter name for start index.
        max_key: Query parameter name for max results.
        max_results: Number of items to fetch per page.

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.pagination import PaginatedAPI

        # Basic usage
        paginator = PaginatedAPI(
            client=LOGIN,
            endpoint_func=endpoint.get_projects,
            results_key="values"
        )

        for project in paginator:
            print(f"Project: {project['key']} - {project['name']}")

        # With custom page size
        paginator = PaginatedAPI(
            client=LOGIN,
            endpoint_func=endpoint.search_users,
            results_key="values",
            max_results=100
        )

        # Get total count
        print(f"Total users: {paginator.total}")
    """

    def __init__(
        self,
        client: Any,
        endpoint_func: Callable[..., str],
        results_key: str = "values",
        total_key: str = "total",
        start_key: str = "start_at",
        max_key: str = "max_results",
        max_results: int = 50,
        endpoint_kwargs: Optional[Dict] = None,
        retry_on_rate_limit: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize the paginated API iterator.

        :param client: Authenticated client with get() method
        :param endpoint_func: Function that returns endpoint URL
        :param results_key: Key containing results in response
        :param total_key: Key containing total count in response
        :param start_key: Parameter name for start index
        :param max_key: Parameter name for max results per page
        :param max_results: Number of results per page (default: 50)
        :param endpoint_kwargs: Additional kwargs to pass to endpoint_func
        :param retry_on_rate_limit: Whether to retry on 429 errors
        :param max_retries: Maximum retry attempts for rate limiting
        """
        self.client = client
        self.endpoint_func = endpoint_func
        self.results_key = results_key
        self.total_key = total_key
        self.start_key = start_key
        self.max_key = max_key
        self.max_results = max_results
        self.endpoint_kwargs = endpoint_kwargs or {}
        self.retry_on_rate_limit = retry_on_rate_limit
        self.max_retries = max_retries

        self._start_at = 0
        self._total: Optional[int] = None
        self._exhausted = False
        self._current_page: List = []
        self._page_index = 0

    @property
    def total(self) -> Optional[int]:
        """Return the total number of items, if known."""
        return self._total

    def _fetch_page(self) -> List:
        """Fetch the next page of results.

        :return: List of items from the response
        :raises JiraAPIError: On API errors
        :raises JiraRateLimitError: On rate limit exceeded
        """
        kwargs = {
            self.start_key: self._start_at,
            self.max_key: self.max_results,
            **self.endpoint_kwargs,
        }

        url = self.endpoint_func(**kwargs)
        retries = 0

        while True:
            response = self.client.get(url)

            if response.status_code == 429 and self.retry_on_rate_limit:
                if retries >= self.max_retries:
                    from jiraone.exceptions import JiraRateLimitError
                    retry_after = response.headers.get("Retry-After", 60)
                    raise JiraRateLimitError(
                        message="Rate limit exceeded after max retries",
                        retry_after=int(retry_after) if retry_after else None,
                    )
                retry_after = int(response.headers.get("Retry-After", 60))
                time.sleep(retry_after)
                retries += 1
                continue

            if response.status_code >= 400:
                from jiraone.exceptions import raise_for_status
                raise_for_status(response)

            break

        data = response.json()

        # Update total if available
        if self._total is None and self.total_key in data:
            self._total = data[self.total_key]

        # Get results
        results = data.get(self.results_key, [])

        # Check if we've reached the end
        if not results:
            self._exhausted = True
            return []

        # Update start for next page
        self._start_at += len(results)

        # Check if we've fetched all items
        if self._total is not None and self._start_at >= self._total:
            self._exhausted = True

        return results

    def __iter__(self) -> Iterator:
        """Return the iterator object."""
        return self

    def __next__(self) -> Any:
        """Return the next item.

        :return: Next item from the paginated results
        :raises StopIteration: When all items have been returned
        """
        # If we have items in current page, return next one
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        # If exhausted, stop iteration
        if self._exhausted:
            raise StopIteration

        # Fetch next page
        self._current_page = self._fetch_page()
        self._page_index = 0

        if not self._current_page:
            raise StopIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    def reset(self) -> None:
        """Reset the iterator to the beginning."""
        self._start_at = 0
        self._total = None
        self._exhausted = False
        self._current_page = []
        self._page_index = 0

    def pages(self) -> Generator[List, None, None]:
        """Iterate over pages instead of individual items.

        Yields entire pages (lists of items) rather than individual items.
        Useful when processing items in batches.

        :return: Generator yielding lists of items

        Example::

            paginator = PaginatedAPI(client=LOGIN, endpoint_func=endpoint.get_projects)
            for page in paginator.pages():
                print(f"Processing batch of {len(page)} projects")
                for project in page:
                    process(project)
        """
        while not self._exhausted:
            page = self._fetch_page()
            if page:
                yield page

    def collect(self, max_items: Optional[int] = None) -> List:
        """Collect all items into a list.

        Warning: This loads all items into memory. Use with caution
        for large datasets.

        :param max_items: Maximum number of items to collect (None = all)
        :return: List of all items

        Example::

            paginator = PaginatedAPI(client=LOGIN, endpoint_func=endpoint.get_projects)
            all_projects = paginator.collect()
            print(f"Found {len(all_projects)} projects")
        """
        items = []
        for item in self:
            items.append(item)
            if max_items is not None and len(items) >= max_items:
                break
        return items


class SearchResultsIterator:
    """Iterator for Jira search (JQL) results.

    Specialized iterator for handling JQL search results which have
    a slightly different pagination structure.

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.pagination import SearchResultsIterator

        jql = "project = TEST ORDER BY created DESC"
        for issue in SearchResultsIterator(LOGIN, jql):
            print(f"{issue['key']}: {issue['fields']['summary']}")
    """

    def __init__(
        self,
        client: Any,
        jql: str,
        fields: Optional[List[str]] = None,
        expand: Optional[str] = None,
        max_results: int = 50,
        validate_query: bool = True,
    ) -> None:
        """Initialize the search results iterator.

        :param client: Authenticated client (LOGIN instance)
        :param jql: JQL query string
        :param fields: List of fields to return (default: all)
        :param expand: Expand parameter for additional data
        :param max_results: Results per page (default: 50, max: 100)
        :param validate_query: Whether to validate the JQL
        """
        self.client = client
        self.jql = jql
        self.fields = fields
        self.expand = expand
        self.max_results = min(max_results, 100)  # Jira limit
        self.validate_query = validate_query

        self._start_at = 0
        self._total: Optional[int] = None
        self._exhausted = False
        self._current_page: List = []
        self._page_index = 0

    @property
    def total(self) -> Optional[int]:
        """Return the total number of matching issues."""
        return self._total

    def _build_url(self) -> str:
        """Build the search URL with current parameters."""
        from urllib.parse import quote

        # Import endpoint at runtime to avoid circular imports
        try:
            from jiraone.access import endpoint
            return endpoint.search_issues_jql(
                query=quote(self.jql),
                start_at=self._start_at,
                max_results=self.max_results
            )
        except ImportError:
            # Fallback if access module not available
            from jiraone.access import LOGIN
            base = LOGIN.base_url
            api_version = "3" if LOGIN.api else "latest"
            return (
                f"{base}/rest/api/{api_version}/search"
                f"?jql={quote(self.jql)}"
                f"&startAt={self._start_at}"
                f"&maxResults={self.max_results}"
            )

    def _fetch_page(self) -> List:
        """Fetch the next page of search results."""
        url = self._build_url()
        response = self.client.get(url)

        if response.status_code >= 400:
            from jiraone.exceptions import raise_for_status
            raise_for_status(response)

        data = response.json()

        if self._total is None:
            self._total = data.get("total", 0)

        issues = data.get("issues", [])

        if not issues:
            self._exhausted = True
            return []

        self._start_at += len(issues)

        if self._start_at >= self._total:
            self._exhausted = True

        return issues

    def __iter__(self) -> Iterator:
        """Return the iterator object."""
        return self

    def __next__(self) -> Dict:
        """Return the next issue.

        :return: Issue dictionary
        :raises StopIteration: When all issues have been returned
        """
        if self._page_index < len(self._current_page):
            item = self._current_page[self._page_index]
            self._page_index += 1
            return item

        if self._exhausted:
            raise StopIteration

        self._current_page = self._fetch_page()
        self._page_index = 0

        if not self._current_page:
            raise StopIteration

        item = self._current_page[self._page_index]
        self._page_index += 1
        return item

    def reset(self) -> None:
        """Reset the iterator to the beginning."""
        self._start_at = 0
        self._total = None
        self._exhausted = False
        self._current_page = []
        self._page_index = 0


def paginate(
    client: Any,
    endpoint_func: Callable[..., str],
    results_key: str = "values",
    max_results: int = 50,
    **kwargs
) -> Generator[Any, None, None]:
    """Convenience generator for paginated API requests.

    A simpler functional interface for pagination when you don't need
    the full PaginatedAPI class features.

    :param client: Authenticated client with get() method
    :param endpoint_func: Function that returns endpoint URL
    :param results_key: Key containing results in response
    :param max_results: Number of results per page
    :param kwargs: Additional kwargs passed to endpoint_func

    :return: Generator yielding individual items

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.pagination import paginate

        for project in paginate(LOGIN, endpoint.get_projects):
            print(project["name"])
    """
    paginator = PaginatedAPI(
        client=client,
        endpoint_func=endpoint_func,
        results_key=results_key,
        max_results=max_results,
        endpoint_kwargs=kwargs,
    )
    yield from paginator
