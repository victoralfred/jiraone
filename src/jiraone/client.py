#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""HTTP client with connection pooling for Jira API requests.

This module provides an enhanced HTTP client that uses connection pooling
for better performance when making multiple API requests.

Features:
    - Connection pooling via requests.Session
    - Configurable pool size
    - Automatic retry on connection errors
    - Context manager support
    - Request/response logging

Example::

    from jiraone.client import JiraClient

    # Using as context manager (recommended)
    with JiraClient(
        base_url="https://example.atlassian.net",
        user="email@example.com",
        token="api-token"
    ) as client:
        response = client.get("/rest/api/3/myself")
        print(response.json())

    # Or configure connection pool
    client = JiraClient(
        base_url="https://example.atlassian.net",
        user="email@example.com",
        token="api-token",
        pool_connections=10,
        pool_maxsize=20,
    )
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from jiraone.exceptions import (
    JiraAPIError,
    JiraAuthenticationError,
    JiraValidationError,
    raise_for_status,
)
from jiraone.jira_logs import add_log


@dataclass
class ClientConfig:
    """Configuration for JiraClient.

    Attributes:
        pool_connections: Number of connection pools to cache (default: 10)
        pool_maxsize: Maximum connections per pool (default: 10)
        max_retries: Maximum retry attempts for failed connections (default: 3)
        backoff_factor: Backoff factor for retries (default: 0.3)
        timeout: Request timeout in seconds (default: 30)
        verify_ssl: Whether to verify SSL certificates (default: True)
        api_version: Jira API version to use (default: "3")

    Example::

        config = ClientConfig(
            pool_connections=20,
            pool_maxsize=30,
            timeout=60,
        )
        client = JiraClient(base_url=url, user=user, token=token, config=config)
    """

    pool_connections: int = 10
    pool_maxsize: int = 10
    max_retries: int = 3
    backoff_factor: float = 0.3
    timeout: int = 30
    verify_ssl: bool = True
    api_version: str = "3"
    retry_status_forcelist: tuple = field(
        default_factory=lambda: (500, 502, 503, 504)
    )


class JiraClient:
    """HTTP client with connection pooling for Jira API.

    This client provides efficient HTTP communication with Jira using
    connection pooling to reuse connections across requests.

    Attributes:
        base_url: The base URL of the Jira instance.
        session: The underlying requests Session.

    Example::

        # Basic usage
        client = JiraClient(
            base_url="https://example.atlassian.net",
            user="email@example.com",
            token="your-api-token"
        )

        # Make requests
        response = client.get("/rest/api/3/myself")
        projects = client.get("/rest/api/3/project").json()

        # Using context manager for automatic cleanup
        with JiraClient(base_url=url, user=user, token=token) as client:
            response = client.get("/rest/api/3/issue/TEST-1")

        # With custom configuration
        config = ClientConfig(pool_connections=20, timeout=60)
        client = JiraClient(
            base_url=url,
            user=user,
            token=token,
            config=config
        )
    """

    def __init__(
        self,
        base_url: str,
        user: Optional[str] = None,
        token: Optional[str] = None,
        oauth_token: Optional[str] = None,
        config: Optional[ClientConfig] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialize the Jira client.

        :param base_url: Base URL of the Jira instance
        :param user: Username or email for basic auth
        :param token: API token or password for basic auth
        :param oauth_token: OAuth bearer token (alternative to basic auth)
        :param config: Client configuration
        :param session: Optional existing session to use
        """
        self.base_url = base_url.rstrip("/")
        self.config = config or ClientConfig()
        self._closed = False

        # Create or use provided session
        if session:
            self.session = session
        else:
            self.session = self._create_session()

        # Setup authentication
        if oauth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {oauth_token}"
            })
        elif user and token:
            self.session.auth = HTTPBasicAuth(user, token)
        else:
            add_log(
                "No authentication configured. Some endpoints may not be accessible.",
                "debug"
            )

        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _create_session(self) -> requests.Session:
        """Create a new session with connection pooling.

        :return: Configured requests Session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.retry_status_forcelist,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )

        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.config.pool_connections,
            pool_maxsize=self.config.pool_maxsize,
            max_retries=retry_strategy,
        )

        # Mount adapter for both HTTP and HTTPS
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _build_url(self, path: str) -> str:
        """Build full URL from path.

        :param path: API path (e.g., "/rest/api/3/myself")
        :return: Full URL
        """
        if path.startswith(("http://", "https://")):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an HTTP request.

        :param method: HTTP method (GET, POST, PUT, DELETE, etc.)
        :param path: API path or full URL
        :param params: Query parameters
        :param json: JSON payload
        :param data: Form data
        :param headers: Additional headers
        :param timeout: Request timeout (overrides config)
        :param raise_on_error: Whether to raise on HTTP errors
        :param kwargs: Additional arguments to requests

        :return: Response object

        :raises JiraAPIError: On HTTP errors if raise_on_error is True
        """
        if self._closed:
            raise JiraValidationError(
                message="Client has been closed",
                field="client",
            )

        url = self._build_url(path)
        timeout = timeout or self.config.timeout

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                timeout=timeout,
                verify=self.config.verify_ssl,
                **kwargs,
            )

            if raise_on_error:
                raise_for_status(response)

            return response

        except requests.exceptions.Timeout as e:
            add_log(f"Request timeout: {url}", "error")
            raise JiraAPIError(
                message=f"Request timed out after {timeout}s",
                url=url,
                method=method,
            ) from e

        except requests.exceptions.ConnectionError as e:
            add_log(f"Connection error: {url}", "error")
            raise JiraAPIError(
                message=f"Connection failed: {e}",
                url=url,
                method=method,
            ) from e

    def get(
        self,
        path: str,
        params: Optional[Dict] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a GET request.

        :param path: API path
        :param params: Query parameters
        :param kwargs: Additional arguments

        :return: Response object
        """
        return self.request("GET", path, params=params, **kwargs)

    def post(
        self,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a POST request.

        :param path: API path
        :param json: JSON payload
        :param data: Form data
        :param kwargs: Additional arguments

        :return: Response object
        """
        return self.request("POST", path, json=json, data=data, **kwargs)

    def put(
        self,
        path: str,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a PUT request.

        :param path: API path
        :param json: JSON payload
        :param data: Form data
        :param kwargs: Additional arguments

        :return: Response object
        """
        return self.request("PUT", path, json=json, data=data, **kwargs)

    def delete(
        self,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a DELETE request.

        :param path: API path
        :param kwargs: Additional arguments

        :return: Response object
        """
        return self.request("DELETE", path, **kwargs)

    def patch(
        self,
        path: str,
        json: Optional[Any] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a PATCH request.

        :param path: API path
        :param json: JSON payload
        :param kwargs: Additional arguments

        :return: Response object
        """
        return self.request("PATCH", path, json=json, **kwargs)

    def close(self) -> None:
        """Close the session and release connections."""
        if not self._closed:
            self.session.close()
            self._closed = True
            add_log("Client session closed", "debug")

    def __enter__(self) -> "JiraClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close session."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure session is closed."""
        if hasattr(self, "_closed") and not self._closed:
            self.close()


def create_pooled_session(
    pool_connections: int = 10,
    pool_maxsize: int = 10,
    max_retries: int = 3,
    backoff_factor: float = 0.3,
) -> requests.Session:
    """Create a requests Session with connection pooling.

    This is a utility function for creating a pooled session that can be
    used with the existing LOGIN object or other clients.

    :param pool_connections: Number of connection pools to cache
    :param pool_maxsize: Maximum connections per pool
    :param max_retries: Maximum retry attempts
    :param backoff_factor: Backoff factor between retries

    :return: Configured requests Session

    Example::

        from jiraone.client import create_pooled_session

        # Create pooled session
        session = create_pooled_session(pool_connections=20)

        # Use with existing LOGIN
        from jiraone import LOGIN
        LOGIN.session = session
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    )

    adapter = HTTPAdapter(
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        max_retries=retry_strategy,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session
