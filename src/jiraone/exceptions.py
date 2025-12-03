#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exception classes for jiraone.

This module provides a hierarchy of exception classes for handling
various error conditions when interacting with Jira APIs.

Exception Hierarchy:
    JiraOneErrors (base)
    ├── JiraAuthenticationError - Authentication and login failures
    ├── JiraAPIError - General API errors with status codes
    │   ├── JiraRateLimitError - 429 Too Many Requests
    │   ├── JiraNotFoundError - 404 Not Found
    │   └── JiraPermissionError - 403 Forbidden
    ├── JiraValidationError - Input validation failures
    ├── JiraFieldError - Field-related errors
    ├── JiraUserError - User-related errors
    └── JiraFileError - File/attachment errors
"""
from typing import Any, Dict, Optional


class JiraOneErrors(Exception):
    """Base class for all jiraone exceptions.

    This class maintains backward compatibility with the original
    error handling system while providing a foundation for more
    specific exception types.

    Attributes:
        errors: Error category string (legacy).
        messages: Error message string.
    """

    def __init__(
        self,
        errors: str = None,
        messages: str = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """Initialize the exception.

        :param errors: Error category (name, value, login, user, file, wrong)
        :param messages: Custom error message
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        self.errors = errors
        self.messages = messages
        super().__init__(self.__str__())

    def __missing_field_value__(self) -> None:
        """A field value is missing or doesn't exist."""
        pass

    def __missing_field_name__(self) -> None:
        """A field name is missing or doesn't exist."""
        pass

    def __login_issues__(self) -> None:
        """An issue with authenticating logins."""
        pass

    def __user_not_found__(self) -> None:
        """An Atlassian user cannot be found."""
        pass

    def __file_extraction__(self) -> None:
        """An issue with either downloading or uploading an attachment."""
        pass

    def __wrong_method_used__(self) -> None:
        """The data being posted is incorrect."""
        pass

    def __str__(self) -> str:
        """Return the representation of the error messages."""
        err = self.errors
        if err == "name":
            msg = self.messages or self.__missing_field_name__.__doc__
        elif err == "value":
            msg = self.messages or self.__missing_field_value__.__doc__
        elif err == "login":
            msg = self.messages or self.__login_issues__.__doc__
        elif err == "user":
            msg = self.messages or self.__user_not_found__.__doc__
        elif err == "file":
            msg = self.messages or self.__file_extraction__.__doc__
        else:
            msg = self.messages or self.__wrong_method_used__.__doc__
        return f"<JiraOneError: {msg}>"


class JiraAuthenticationError(JiraOneErrors):
    """Raised when authentication to Jira fails.

    This includes invalid credentials, expired tokens, and OAuth failures.

    Example::

        try:
            LOGIN(user="invalid", password="wrong", url="https://example.atlassian.net")
        except JiraAuthenticationError as e:
            print(f"Login failed: {e}")
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: Optional[int] = None,
        response_body: Optional[Dict] = None,
    ) -> None:
        """Initialize the authentication error.

        :param message: Error description
        :param status_code: HTTP status code if available
        :param response_body: API response body if available
        """
        self.status_code = status_code
        self.response_body = response_body
        super().__init__("login", message)

    def __str__(self) -> str:
        """Return formatted error message."""
        base_msg = self.messages or "Authentication failed"
        if self.status_code:
            return f"<JiraAuthenticationError: {base_msg} (HTTP {self.status_code})>"
        return f"<JiraAuthenticationError: {base_msg}>"


class JiraAPIError(JiraOneErrors):
    """Raised when a Jira API request fails.

    This is a general API error that includes HTTP status code and
    response details for debugging.

    Attributes:
        status_code: HTTP status code from the response.
        response_body: Parsed JSON response body.
        url: The URL that was requested.
        method: The HTTP method used.

    Example::

        try:
            response = LOGIN.get(endpoint.get_projects())
            if response.status_code >= 400:
                raise JiraAPIError.from_response(response)
        except JiraAPIError as e:
            print(f"API error: {e.status_code} - {e.message}")
    """

    def __init__(
        self,
        message: str = "API request failed",
        status_code: Optional[int] = None,
        response_body: Optional[Dict] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Initialize the API error.

        :param message: Error description
        :param status_code: HTTP status code
        :param response_body: API response body
        :param url: Request URL
        :param method: HTTP method
        """
        self.status_code = status_code
        self.response_body = response_body
        self.url = url
        self.method = method
        super().__init__("wrong", message)

    @classmethod
    def from_response(cls, response: Any, message: str = None) -> "JiraAPIError":
        """Create an exception from a requests Response object.

        :param response: requests.Response object
        :param message: Optional custom message

        :return: JiraAPIError instance
        """
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text[:500] if hasattr(response, "text") else None}

        error_msg = message
        if not error_msg:
            if "errorMessages" in body and body["errorMessages"]:
                error_msg = "; ".join(body["errorMessages"])
            elif "message" in body:
                error_msg = body["message"]
            else:
                error_msg = f"API request failed with status {response.status_code}"

        return cls(
            message=error_msg,
            status_code=response.status_code,
            response_body=body,
            url=response.url if hasattr(response, "url") else None,
            method=response.request.method if hasattr(response, "request") else None,
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        parts = [f"<JiraAPIError: {self.messages}"]
        if self.status_code:
            parts.append(f" (HTTP {self.status_code})")
        if self.method and self.url:
            parts.append(f" [{self.method} {self.url}]")
        parts.append(">")
        return "".join(parts)


class JiraRateLimitError(JiraAPIError):
    """Raised when API rate limit is exceeded (HTTP 429).

    This error indicates that too many requests have been made
    and the client should retry after a delay.

    Attributes:
        retry_after: Seconds to wait before retrying (if provided by API).

    Example::

        try:
            response = LOGIN.get(endpoint.get_projects())
        except JiraRateLimitError as e:
            time.sleep(e.retry_after or 60)
            # Retry the request
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        response_body: Optional[Dict] = None,
    ) -> None:
        """Initialize the rate limit error.

        :param message: Error description
        :param retry_after: Seconds to wait before retrying
        :param response_body: API response body
        """
        self.retry_after = retry_after
        super().__init__(
            message=message,
            status_code=429,
            response_body=response_body,
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        base_msg = self.messages or "Rate limit exceeded"
        if self.retry_after:
            return f"<JiraRateLimitError: {base_msg} (retry after {self.retry_after}s)>"
        return f"<JiraRateLimitError: {base_msg}>"


class JiraNotFoundError(JiraAPIError):
    """Raised when a requested resource is not found (HTTP 404).

    Example::

        try:
            response = LOGIN.get(endpoint.issues("INVALID-123"))
        except JiraNotFoundError as e:
            print(f"Issue not found: {e}")
    """

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        response_body: Optional[Dict] = None,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Initialize the not found error.

        :param message: Error description
        :param resource_type: Type of resource (e.g., "issue", "project")
        :param resource_id: ID of the resource
        :param response_body: API response body
        :param status_code: HTTP status code (defaults to 404)
        :param url: Request URL
        :param method: HTTP method
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            message=message,
            status_code=status_code or 404,
            response_body=response_body,
            url=url,
            method=method,
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.resource_type and self.resource_id:
            return f"<JiraNotFoundError: {self.resource_type} '{self.resource_id}' not found>"
        return f"<JiraNotFoundError: {self.messages}>"


class JiraPermissionError(JiraAPIError):
    """Raised when the user lacks permission for an operation (HTTP 403).

    Example::

        try:
            response = LOGIN.delete(endpoint.projects("ADMIN-PROJECT"))
        except JiraPermissionError as e:
            print(f"Permission denied: {e}")
    """

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        response_body: Optional[Dict] = None,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
    ) -> None:
        """Initialize the permission error.

        :param message: Error description
        :param required_permission: The permission that was required
        :param response_body: API response body
        :param status_code: HTTP status code (defaults to 403)
        :param url: Request URL
        :param method: HTTP method
        """
        self.required_permission = required_permission
        super().__init__(
            message=message,
            status_code=status_code or 403,
            response_body=response_body,
            url=url,
            method=method,
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.required_permission:
            return f"<JiraPermissionError: {self.messages} (requires: {self.required_permission})>"
        return f"<JiraPermissionError: {self.messages}>"


class JiraValidationError(JiraOneErrors):
    """Raised when input validation fails.

    Use this for validating user input before making API requests.

    Example::

        if not url.startswith("https://"):
            raise JiraValidationError("URL must use HTTPS", field="url")
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Any = None,
    ) -> None:
        """Initialize the validation error.

        :param message: Error description
        :param field: Name of the field that failed validation
        :param value: The invalid value
        """
        self.field = field
        self.value = value
        super().__init__("value", message)

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.field:
            return f"<JiraValidationError: {self.messages} (field: {self.field})>"
        return f"<JiraValidationError: {self.messages}>"


class JiraFieldError(JiraOneErrors):
    """Raised when there's an error with a Jira field.

    Example::

        try:
            field.update_field_data(data, "Custom Field", key_or_id="ISSUE-1")
        except JiraFieldError as e:
            print(f"Field error: {e}")
    """

    def __init__(
        self,
        message: str = "Field error",
        field_name: Optional[str] = None,
        field_id: Optional[str] = None,
    ) -> None:
        """Initialize the field error.

        :param message: Error description
        :param field_name: Name of the field
        :param field_id: ID of the field
        """
        self.field_name = field_name
        self.field_id = field_id
        super().__init__("name", message)

    def __str__(self) -> str:
        """Return formatted error message."""
        field_info = self.field_name or self.field_id
        if field_info:
            return f"<JiraFieldError: {self.messages} (field: {field_info})>"
        return f"<JiraFieldError: {self.messages}>"


class JiraUserError(JiraOneErrors):
    """Raised when there's an error related to a Jira user.

    Example::

        try:
            user = USER.search_user("nonexistent@example.com")
        except JiraUserError as e:
            print(f"User error: {e}")
    """

    def __init__(
        self,
        message: str = "User error",
        account_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> None:
        """Initialize the user error.

        :param message: Error description
        :param account_id: Atlassian account ID
        :param email: User email address
        """
        self.account_id = account_id
        self.email = email
        super().__init__("user", message)

    def __str__(self) -> str:
        """Return formatted error message."""
        user_info = self.email or self.account_id
        if user_info:
            return f"<JiraUserError: {self.messages} (user: {user_info})>"
        return f"<JiraUserError: {self.messages}>"


class JiraFileError(JiraOneErrors):
    """Raised when there's an error with file operations.

    This includes attachment upload/download failures.

    Example::

        try:
            PROJECT.download_attachments("ISSUE-1")
        except JiraFileError as e:
            print(f"File error: {e}")
    """

    def __init__(
        self,
        message: str = "File operation failed",
        filename: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> None:
        """Initialize the file error.

        :param message: Error description
        :param filename: Name of the file
        :param operation: Operation that failed (upload, download, delete)
        """
        self.filename = filename
        self.operation = operation
        super().__init__("file", message)

    def __str__(self) -> str:
        """Return formatted error message."""
        parts = [f"<JiraFileError: {self.messages}"]
        if self.operation:
            parts.append(f" ({self.operation})")
        if self.filename:
            parts.append(f" [{self.filename}]")
        parts.append(">")
        return "".join(parts)


class JiraTimeoutError(JiraAPIError):
    """Raised when an API request times out.

    Example::

        try:
            response = LOGIN.get(endpoint.get_projects(), timeout=5)
        except JiraTimeoutError as e:
            print(f"Request timed out: {e}")
    """

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: Optional[float] = None,
        url: Optional[str] = None,
    ) -> None:
        """Initialize the timeout error.

        :param message: Error description
        :param timeout: Timeout value in seconds
        :param url: Request URL
        """
        self.timeout = timeout
        super().__init__(
            message=message,
            status_code=None,
            url=url,
        )

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.timeout:
            return f"<JiraTimeoutError: {self.messages} (timeout: {self.timeout}s)>"
        return f"<JiraTimeoutError: {self.messages}>"


# Convenience function for raising API errors from responses
def raise_for_status(response: Any, message: str = None) -> None:
    """Raise an appropriate exception for HTTP error responses.

    :param response: requests.Response object
    :param message: Optional custom error message

    :raises JiraRateLimitError: For 429 responses
    :raises JiraNotFoundError: For 404 responses
    :raises JiraPermissionError: For 403 responses
    :raises JiraAuthenticationError: For 401 responses
    :raises JiraAPIError: For other error responses
    """
    if response.status_code < 400:
        return

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise JiraRateLimitError(
            message=message or "Rate limit exceeded",
            retry_after=int(retry_after) if retry_after else None,
        )
    elif response.status_code == 404:
        raise JiraNotFoundError.from_response(response, message)
    elif response.status_code == 403:
        raise JiraPermissionError.from_response(response, message)
    elif response.status_code == 401:
        raise JiraAuthenticationError(
            message=message or "Authentication required",
            status_code=401,
        )
    else:
        raise JiraAPIError.from_response(response, message)
