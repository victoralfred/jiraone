#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retry utilities with exponential backoff for Jira API requests.

This module provides decorators and utilities for handling transient
failures in API requests, particularly rate limiting (429) and
server errors (503).

Example::

    from jiraone.retry import with_retry, RetryConfig

    # Using decorator with default settings
    @with_retry()
    def fetch_projects():
        return LOGIN.get(endpoint.get_projects())

    # With custom configuration
    @with_retry(max_attempts=5, base_delay=2.0)
    def fetch_issues(jql):
        return LOGIN.get(endpoint.search_issues_jql(jql))
"""
import functools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Set, Tuple, TypeVar, Union

from jiraone.exceptions import (
    JiraAPIError,
    JiraRateLimitError,
    JiraTimeoutError,
)
from jiraone.jira_logs import add_log

# Type variable for generic return type
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        retryable_status_codes: HTTP status codes that should trigger retry
        retryable_exceptions: Exception types that should trigger retry

    Example::

        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
        )
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: Set[int] = field(
        default_factory=lambda: {429, 500, 502, 503, 504}
    )
    retryable_exceptions: Tuple = field(
        default_factory=lambda: (
            JiraRateLimitError,
            JiraTimeoutError,
            ConnectionError,
            TimeoutError,
        )
    )

    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate the delay for a given attempt number.

        :param attempt: Current attempt number (0-indexed)
        :param retry_after: Optional Retry-After header value

        :return: Delay in seconds
        """
        # If Retry-After header is provided, use it
        if retry_after is not None:
            return min(float(retry_after), self.max_delay)

        # Calculate exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay


# Default configuration
DEFAULT_CONFIG = RetryConfig()


def with_retry(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that adds retry logic with exponential backoff.

    Can be used with or without parameters.

    :param max_attempts: Maximum retry attempts (overrides config)
    :param base_delay: Base delay in seconds (overrides config)
    :param max_delay: Maximum delay (overrides config)
    :param config: Full RetryConfig object
    :param on_retry: Callback called before each retry (attempt, exception, delay)

    :return: Decorated function with retry logic

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.retry import with_retry

        # Basic usage
        @with_retry()
        def get_projects():
            return LOGIN.get(endpoint.get_projects())

        # With custom settings
        @with_retry(max_attempts=5, base_delay=2.0)
        def get_issues(jql):
            return LOGIN.get(endpoint.search_issues_jql(jql))

        # With callback for logging
        def log_retry(attempt, exc, delay):
            print(f"Retry {attempt}: {exc}, waiting {delay}s")

        @with_retry(on_retry=log_retry)
        def resilient_request():
            return LOGIN.get(endpoint.myself())
    """
    # Create or update config
    retry_config = config or RetryConfig()
    if max_attempts is not None:
        retry_config.max_attempts = max_attempts
    if base_delay is not None:
        retry_config.base_delay = base_delay
    if max_delay is not None:
        retry_config.max_delay = max_delay

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(retry_config.max_attempts):
                try:
                    result = func(*args, **kwargs)

                    # Check if result is a Response with retryable status
                    if hasattr(result, "status_code"):
                        if result.status_code in retry_config.retryable_status_codes:
                            retry_after = result.headers.get("Retry-After")
                            delay = retry_config.calculate_delay(
                                attempt,
                                int(retry_after) if retry_after else None
                            )

                            if attempt < retry_config.max_attempts - 1:
                                add_log(
                                    f"Retryable status {result.status_code}, "
                                    f"attempt {attempt + 1}/{retry_config.max_attempts}, "
                                    f"waiting {delay:.2f}s",
                                    "debug"
                                )

                                if on_retry:
                                    exc = JiraAPIError(
                                        message=f"HTTP {result.status_code}",
                                        status_code=result.status_code,
                                    )
                                    on_retry(attempt + 1, exc, delay)

                                time.sleep(delay)
                                continue

                    return result

                except retry_config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < retry_config.max_attempts - 1:
                        # Get retry-after from exception if available
                        retry_after = getattr(e, "retry_after", None)
                        delay = retry_config.calculate_delay(attempt, retry_after)

                        add_log(
                            f"Retryable error: {type(e).__name__}: {e}, "
                            f"attempt {attempt + 1}/{retry_config.max_attempts}, "
                            f"waiting {delay:.2f}s",
                            "debug"
                        )

                        if on_retry:
                            on_retry(attempt + 1, e, delay)

                        time.sleep(delay)
                    else:
                        raise

            # All retries exhausted
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error: no result or exception")

        return wrapper
    return decorator


def retry_request(
    request_func: Callable[..., Any],
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any
) -> Any:
    """Execute a request function with retry logic.

    Functional alternative to the @with_retry decorator.

    :param request_func: Function to call
    :param args: Positional arguments for the function
    :param config: Retry configuration
    :param kwargs: Keyword arguments for the function

    :return: Result of the request function

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.retry import retry_request

        # Simple usage
        response = retry_request(LOGIN.get, endpoint.get_projects())

        # With custom config
        config = RetryConfig(max_attempts=5)
        response = retry_request(
            LOGIN.post,
            endpoint.issues(),
            config=config,
            payload=issue_data
        )
    """
    retry_config = config or DEFAULT_CONFIG

    @with_retry(config=retry_config)
    def _wrapped():
        return request_func(*args, **kwargs)

    return _wrapped()


class RetrySession:
    """Context manager for requests with automatic retry.

    Wraps a client to add retry logic to all requests.

    Example::

        from jiraone import LOGIN, endpoint
        from jiraone.retry import RetrySession

        with RetrySession(LOGIN) as session:
            # All requests through session have retry logic
            projects = session.get(endpoint.get_projects())
            issues = session.get(endpoint.search_issues_jql("project=TEST"))
    """

    def __init__(
        self,
        client: Any,
        config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize the retry session.

        :param client: The underlying client (e.g., LOGIN)
        :param config: Retry configuration
        """
        self.client = client
        self.config = config or DEFAULT_CONFIG

    def __enter__(self) -> "RetrySession":
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        pass

    def get(self, url: str, **kwargs: Any) -> Any:
        """Make a GET request with retry logic."""
        return retry_request(self.client.get, url, config=self.config, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        """Make a POST request with retry logic."""
        return retry_request(self.client.post, url, config=self.config, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Any:
        """Make a PUT request with retry logic."""
        return retry_request(self.client.put, url, config=self.config, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Any:
        """Make a DELETE request with retry logic."""
        return retry_request(self.client.delete, url, config=self.config, **kwargs)
