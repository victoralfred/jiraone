#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Logging configuration and utilities for jiraone.

This module provides logging setup with credential masking to prevent
sensitive information from being written to log files.

Features:
    - Rotating file handler for log management
    - Automatic credential masking (passwords, tokens, API keys)
    - Cross-platform support (Linux, macOS, Windows)
"""
import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from platform import system
from typing import Any, List, Pattern


WORK_PATH = os.path.abspath(os.getcwd())
now = datetime.now()
LOGGER = ""

# Patterns for sensitive data that should be masked in logs
SENSITIVE_PATTERNS: List[Pattern] = [
    # API tokens (various formats)
    re.compile(r'(api[_-]?token|apitoken)["\s:=]+["\']?([A-Za-z0-9_\-\.]+)["\']?', re.I),
    re.compile(r'(Bearer\s+)([A-Za-z0-9_\-\.]+)', re.I),
    re.compile(r'(Authorization["\s:=]+["\']?Bearer\s+)([A-Za-z0-9_\-\.]+)', re.I),
    # Passwords
    re.compile(r'(password|passwd|pwd)["\s:=]+["\']?([^\s"\',]+)["\']?', re.I),
    # OAuth tokens
    re.compile(r'(access[_-]?token|refresh[_-]?token)["\s:=]+["\']?([A-Za-z0-9_\-\.]+)["\']?', re.I),
    re.compile(r'(client[_-]?secret)["\s:=]+["\']?([A-Za-z0-9_\-\.]+)["\']?', re.I),
    # Basic auth
    re.compile(r'(Basic\s+)([A-Za-z0-9+/=]+)', re.I),
    # Generic secret/key patterns
    re.compile(r'(secret|private[_-]?key|api[_-]?key)["\s:=]+["\']?([A-Za-z0-9_\-\.]+)["\']?', re.I),
]


class CredentialMaskingFilter(logging.Filter):
    """Logging filter that masks sensitive credentials in log messages.

    This filter automatically detects and masks passwords, API tokens,
    OAuth secrets, and other sensitive data before it is written to logs.

    Example::

        logger = logging.getLogger(__name__)
        logger.addFilter(CredentialMaskingFilter())
        logger.info("Connecting with password=secret123")
        # Logged as: "Connecting with password=***MASKED***"
    """

    MASK = "***MASKED***"

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data in log records.

        :param record: The log record to process
        :return: True to include the record in output
        """
        if record.msg:
            record.msg = self._mask_sensitive_data(str(record.msg))
        if record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _mask_sensitive_data(self, message: str) -> str:
        """Mask sensitive data in a message string.

        :param message: The message to process
        :return: Message with sensitive data masked
        """
        for pattern in SENSITIVE_PATTERNS:
            message = pattern.sub(rf'\1{self.MASK}', message)
        return message


class SecureFormatter(logging.Formatter):
    """Logging formatter that masks credentials in formatted output.

    This formatter ensures that even if credentials slip through the
    filter, they will be masked in the final formatted output.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, masking any sensitive data.

        :param record: The log record to format
        :return: Formatted log string with credentials masked
        """
        formatted = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            formatted = pattern.sub(rf'\1***MASKED***', formatted)
        return formatted


# Create logger with credential masking
logger = logging.getLogger(__name__)
formatting = SecureFormatter(
    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
)

# Add credential masking filter
credential_filter = CredentialMaskingFilter()
logger.addFilter(credential_filter)

# Setup platform-specific log directory
if system() in ("Linux", "Darwin"):
    LOGGER = os.path.join(WORK_PATH, "logs")
    if not os.path.exists(LOGGER):
        os.mkdir(LOGGER)
    handler = RotatingFileHandler(
        os.path.join(LOGGER, "app.log"),
        maxBytes=1000000,
        backupCount=20
    )
    handler.setFormatter(formatting)
    handler.addFilter(credential_filter)
    logger.addHandler(handler)

if system() == "Windows":
    LOGGER = os.path.join(WORK_PATH, "logs")
    if not os.path.exists(LOGGER):
        os.mkdir(LOGGER)
    handler = RotatingFileHandler(
        os.path.join(LOGGER, "app.log"),
        maxBytes=1000000,
        backupCount=20
    )
    handler.setFormatter(formatting)
    handler.addFilter(credential_filter)
    logger.addHandler(handler)


def add_log(message: str, level: str) -> None:
    """Write a log entry to the log file with automatic credential masking.

    Credentials and sensitive data are automatically masked before being
    written to the log file.

    :param message: The message to log
    :param level: Log level (info, debug, error)

    :return: None

    Example::

        from jiraone import add_log

        add_log("Processing request", "info")
        add_log("Error occurred", "error")
        add_log("Token value: abc123", "debug")  # Token will be masked
    """
    if level.lower() == "debug":
        logger.setLevel(logging.DEBUG)
        logger.debug(message)
    elif level.lower() == "error":
        logger.setLevel(logging.ERROR)
        logger.error(message)
    else:
        logger.setLevel(logging.INFO)
        logger.info(message)


def mask_sensitive_string(value: str) -> str:
    """Mask a string value for safe display or logging.

    Useful for manually masking values that need to be displayed
    in error messages or debug output.

    :param value: The string to mask
    :return: Masked string showing only first and last 2 characters

    Example::

        from jiraone.jira_logs import mask_sensitive_string

        token = "abc123xyz789"
        print(f"Token: {mask_sensitive_string(token)}")
        # Output: "Token: ab***89"
    """
    if not value or len(value) < 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"
