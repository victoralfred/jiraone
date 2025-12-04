#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for jiraone.retry module."""
import pytest
import sys
sys.path.insert(0, 'src')

from jiraone.retry import (
    RetryConfig,
    with_retry,
    retry_request,
    RetrySession,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert 429 in config.retryable_status_codes

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0

    def test_calculate_delay_basic(self):
        """Test basic delay calculation."""
        config = RetryConfig(base_delay=1.0, jitter=False)
        delay = config.calculate_delay(0)
        assert delay == 1.0  # 1.0 * 2^0 = 1.0

    def test_calculate_delay_exponential(self):
        """Test exponential delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        assert config.calculate_delay(0) == 1.0   # 1.0 * 2^0
        assert config.calculate_delay(1) == 2.0   # 1.0 * 2^1
        assert config.calculate_delay(2) == 4.0   # 1.0 * 2^2
        assert config.calculate_delay(3) == 8.0   # 1.0 * 2^3

    def test_calculate_delay_max_limit(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)
        delay = config.calculate_delay(10)  # Would be 1024 without cap
        assert delay == 5.0

    def test_calculate_delay_with_retry_after(self):
        """Test delay calculation with Retry-After header."""
        config = RetryConfig(max_delay=60.0)
        delay = config.calculate_delay(0, retry_after=30)
        assert delay == 30.0

    def test_calculate_delay_retry_after_capped(self):
        """Test that Retry-After is capped at max_delay."""
        config = RetryConfig(max_delay=60.0)
        delay = config.calculate_delay(0, retry_after=120)
        assert delay == 60.0


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful call doesn't retry."""
        call_count = 0

        @with_retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test retry on exception."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        call_count = 0

        @with_retry(max_attempts=2, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()
        assert call_count == 2

    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()
        assert call_count == 1

    def test_callback_on_retry(self):
        """Test that callback is called on retry."""
        retries = []

        def on_retry(attempt, exc, delay):
            retries.append((attempt, type(exc).__name__))

        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, on_retry=on_retry)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Flaky")
            return "ok"

        flaky_func()
        assert len(retries) == 2
        assert retries[0][0] == 1  # First retry attempt
        assert retries[1][0] == 2  # Second retry attempt

    def test_response_with_retryable_status(self):
        """Test retry on response with retryable status code."""
        call_count = 0

        class MockResponse:
            def __init__(self, status):
                self.status_code = status
                self.headers = {}

        @with_retry(max_attempts=3, base_delay=0.01)
        def returns_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MockResponse(503)
            return MockResponse(200)

        result = returns_error_then_success()
        assert result.status_code == 200
        assert call_count == 3


class TestRetryRequest:
    """Tests for retry_request function."""

    def test_basic_usage(self):
        """Test basic retry_request usage."""
        def successful_request(url):
            return {"status": "ok", "url": url}

        result = retry_request(successful_request, "https://example.com")
        assert result["status"] == "ok"

    def test_with_custom_config(self):
        """Test with custom configuration."""
        config = RetryConfig(max_attempts=5)

        def request_func(url, timeout=30):
            return {"url": url, "timeout": timeout}

        result = retry_request(
            request_func,
            "https://example.com",
            config=config,
            timeout=60
        )
        assert result["timeout"] == 60


class TestRetrySession:
    """Tests for RetrySession context manager."""

    def test_context_manager(self):
        """Test context manager usage."""
        class MockClient:
            def get(self, url):
                return {"url": url, "method": "GET"}

        with RetrySession(MockClient()) as session:
            result = session.get("https://example.com")
        assert result["method"] == "GET"

    def test_different_methods(self):
        """Test different HTTP methods."""
        class MockClient:
            def get(self, url, **kwargs):
                return {"method": "GET"}

            def post(self, url, **kwargs):
                return {"method": "POST"}

            def put(self, url, **kwargs):
                return {"method": "PUT"}

            def delete(self, url, **kwargs):
                return {"method": "DELETE"}

        with RetrySession(MockClient()) as session:
            assert session.get("url")["method"] == "GET"
            assert session.post("url")["method"] == "POST"
            assert session.put("url")["method"] == "PUT"
            assert session.delete("url")["method"] == "DELETE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
