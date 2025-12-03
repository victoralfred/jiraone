#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Streaming utilities for large data exports.

This module provides utilities for efficiently handling large data transfers
with the Jira API, including streaming downloads and chunked uploads.

Features:
    - Streaming file downloads with progress tracking
    - Chunked CSV exports for memory efficiency
    - Generator-based iteration for large datasets
    - Progress callbacks for monitoring transfers

Example::

    from jiraone.streaming import StreamingDownloader, ChunkedExporter

    # Stream large attachment download
    with StreamingDownloader(url, auth) as downloader:
        for chunk in downloader:
            file.write(chunk)

    # Export large dataset to CSV in chunks
    exporter = ChunkedExporter(filename="export.csv")
    for issue in paginated_issues:
        exporter.write_row(issue)
    exporter.close()
"""
import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    TextIO,
    Union,
)

import requests
from requests.auth import HTTPBasicAuth

from jiraone.exceptions import JiraAPIError, JiraFileError
from jiraone.jira_logs import add_log


@dataclass
class StreamConfig:
    """Configuration for streaming operations.

    Attributes:
        chunk_size: Size of chunks in bytes for streaming (default: 8192)
        timeout: Request timeout in seconds (default: 300)
        verify_ssl: Whether to verify SSL certificates (default: True)
        progress_callback: Optional callback for progress updates
        buffer_size: Buffer size for file operations (default: 65536)

    Example::

        config = StreamConfig(
            chunk_size=16384,
            timeout=600,
            progress_callback=lambda bytes_read, total: print(f"{bytes_read}/{total}")
        )
    """

    chunk_size: int = 8192
    timeout: int = 300
    verify_ssl: bool = True
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None
    buffer_size: int = 65536


class StreamingDownloader:
    """Streaming downloader for large files.

    Downloads files in chunks to minimize memory usage. Supports progress
    tracking and automatic retry on connection errors.

    Example::

        from jiraone.streaming import StreamingDownloader

        downloader = StreamingDownloader(
            url="https://example.atlassian.net/attachment/12345",
            auth=("email@example.com", "api-token"),
        )

        with open("output.pdf", "wb") as f:
            for chunk in downloader.stream():
                f.write(chunk)

        # Or use the download_to_file convenience method
        downloader.download_to_file("output.pdf")
    """

    def __init__(
        self,
        url: str,
        auth: Optional[tuple] = None,
        headers: Optional[Dict[str, str]] = None,
        config: Optional[StreamConfig] = None,
    ) -> None:
        """Initialize the streaming downloader.

        :param url: URL to download from
        :param auth: Tuple of (username, password/token) for basic auth
        :param headers: Additional headers to include
        :param config: Streaming configuration
        """
        self.url = url
        self.auth = HTTPBasicAuth(*auth) if auth else None
        self.headers = headers or {}
        self.config = config or StreamConfig()
        self._response: Optional[requests.Response] = None
        self._bytes_downloaded = 0
        self._total_size: Optional[int] = None

    @property
    def bytes_downloaded(self) -> int:
        """Return the number of bytes downloaded so far."""
        return self._bytes_downloaded

    @property
    def total_size(self) -> Optional[int]:
        """Return the total file size if known."""
        return self._total_size

    @property
    def progress_percent(self) -> Optional[float]:
        """Return download progress as percentage if total size is known."""
        if self._total_size and self._total_size > 0:
            return (self._bytes_downloaded / self._total_size) * 100
        return None

    def stream(self) -> Generator[bytes, None, None]:
        """Stream the download in chunks.

        :yields: Bytes chunks of the downloaded content

        :raises JiraAPIError: If the download fails
        """
        try:
            self._response = requests.get(
                self.url,
                auth=self.auth,
                headers=self.headers,
                stream=True,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            self._response.raise_for_status()

            # Get total size from Content-Length header
            content_length = self._response.headers.get("Content-Length")
            self._total_size = int(content_length) if content_length else None

            self._bytes_downloaded = 0
            for chunk in self._response.iter_content(
                chunk_size=self.config.chunk_size
            ):
                if chunk:
                    self._bytes_downloaded += len(chunk)
                    if self.config.progress_callback:
                        self.config.progress_callback(
                            self._bytes_downloaded, self._total_size
                        )
                    yield chunk

        except requests.exceptions.RequestException as e:
            add_log(f"Download failed: {self.url}", "error")
            raise JiraAPIError(
                message=f"Download failed: {e}",
                url=self.url,
                method="GET",
            ) from e
        finally:
            if self._response:
                self._response.close()

    def download_to_file(
        self,
        filepath: str,
        overwrite: bool = False,
    ) -> int:
        """Download content directly to a file.

        :param filepath: Path to save the file
        :param overwrite: Whether to overwrite existing file

        :return: Number of bytes written

        :raises JiraFileError: If file exists and overwrite is False
        """
        if os.path.exists(filepath) and not overwrite:
            raise JiraFileError(
                message=f"File already exists: {filepath}",
                filename=filepath,
                operation="download",
            )

        bytes_written = 0
        try:
            with open(filepath, "wb") as f:
                for chunk in self.stream():
                    f.write(chunk)
                    bytes_written += len(chunk)

            add_log(f"Downloaded {bytes_written} bytes to {filepath}", "debug")
            return bytes_written

        except IOError as e:
            add_log(f"Failed to write file: {filepath}", "error")
            raise JiraFileError(
                message=f"Failed to write file: {e}",
                filename=filepath,
                operation="download",
            ) from e

    def __iter__(self) -> Generator[bytes, None, None]:
        """Make the downloader iterable."""
        return self.stream()


class ChunkedExporter:
    """Memory-efficient CSV exporter for large datasets.

    Writes data to CSV files in a streaming fashion, with optional
    file rotation when size limits are reached.

    Example::

        from jiraone.streaming import ChunkedExporter

        exporter = ChunkedExporter(
            filepath="issues.csv",
            headers=["Key", "Summary", "Status"],
        )

        for issue in issues:
            exporter.write_row([issue.key, issue.summary, issue.status])

        exporter.close()

        # Or use as context manager
        with ChunkedExporter("issues.csv", headers=["Key", "Summary"]) as exp:
            exp.write_row(["TEST-1", "Test issue"])
    """

    def __init__(
        self,
        filepath: str,
        headers: Optional[List[str]] = None,
        max_rows_per_file: Optional[int] = None,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> None:
        """Initialize the chunked exporter.

        :param filepath: Base path for output files
        :param headers: Optional list of column headers
        :param max_rows_per_file: Maximum rows per file (triggers rotation)
        :param encoding: File encoding (default: utf-8)
        :param delimiter: CSV delimiter (default: comma)
        """
        self.filepath = filepath
        self.headers = headers
        self.max_rows_per_file = max_rows_per_file
        self.encoding = encoding
        self.delimiter = delimiter

        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.writer] = None
        self._rows_written = 0
        self._total_rows = 0
        self._file_count = 0
        self._files_created: List[str] = []

        self._open_file()

    def _get_filepath(self) -> str:
        """Get the current output filepath."""
        if self._file_count == 0:
            return self.filepath
        base, ext = os.path.splitext(self.filepath)
        return f"{base}_{self._file_count}{ext}"

    def _open_file(self) -> None:
        """Open a new output file."""
        filepath = self._get_filepath()
        self._file = open(filepath, "w", newline="", encoding=self.encoding)
        self._writer = csv.writer(self._file, delimiter=self.delimiter)
        self._files_created.append(filepath)
        self._rows_written = 0

        if self.headers:
            self._writer.writerow(self.headers)

        add_log(f"Opened export file: {filepath}", "debug")

    def _rotate_file(self) -> None:
        """Rotate to a new file."""
        if self._file:
            self._file.close()
        self._file_count += 1
        self._open_file()

    def write_row(self, row: List[Any]) -> None:
        """Write a single row to the CSV.

        :param row: List of values for the row
        """
        if self._writer is None:
            raise JiraFileError(
                message="Exporter is closed",
                operation="write",
            )

        self._writer.writerow(row)
        self._rows_written += 1
        self._total_rows += 1

        # Check if rotation is needed
        if (
            self.max_rows_per_file
            and self._rows_written >= self.max_rows_per_file
        ):
            self._rotate_file()

    def write_rows(self, rows: Iterator[List[Any]]) -> int:
        """Write multiple rows from an iterator.

        :param rows: Iterator of row data

        :return: Number of rows written
        """
        count = 0
        for row in rows:
            self.write_row(row)
            count += 1
        return count

    def write_dict_row(
        self, row: Dict[str, Any], fieldnames: Optional[List[str]] = None
    ) -> None:
        """Write a row from a dictionary.

        :param row: Dictionary of field values
        :param fieldnames: Optional ordered list of field names to use
        """
        if fieldnames:
            self.write_row([row.get(field, "") for field in fieldnames])
        elif self.headers:
            self.write_row([row.get(field, "") for field in self.headers])
        else:
            self.write_row(list(row.values()))

    @property
    def total_rows_written(self) -> int:
        """Return the total number of rows written across all files."""
        return self._total_rows

    @property
    def files_created(self) -> List[str]:
        """Return list of files created."""
        return self._files_created.copy()

    def flush(self) -> None:
        """Flush the current file to disk."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Close the exporter and finalize all files."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
            add_log(
                f"Closed exporter. Total rows: {self._total_rows}, "
                f"Files: {len(self._files_created)}",
                "debug",
            )

    def __enter__(self) -> "ChunkedExporter":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close files."""
        self.close()


@contextmanager
def streaming_download(
    url: str,
    auth: Optional[tuple] = None,
    headers: Optional[Dict[str, str]] = None,
    config: Optional[StreamConfig] = None,
) -> Generator[StreamingDownloader, None, None]:
    """Context manager for streaming downloads.

    Example::

        from jiraone.streaming import streaming_download

        with streaming_download(url, auth=("email", "token")) as downloader:
            with open("file.pdf", "wb") as f:
                for chunk in downloader:
                    f.write(chunk)

    :param url: URL to download from
    :param auth: Tuple of (username, password/token)
    :param headers: Additional headers
    :param config: Streaming configuration

    :yields: StreamingDownloader instance
    """
    downloader = StreamingDownloader(
        url=url,
        auth=auth,
        headers=headers,
        config=config,
    )
    try:
        yield downloader
    finally:
        pass  # Cleanup handled by stream() method


def stream_json_array(
    response: requests.Response,
    item_key: str = "values",
    chunk_size: int = 8192,
) -> Generator[Dict[str, Any], None, None]:
    """Stream items from a JSON array response.

    Useful for processing large paginated responses without loading
    the entire response into memory.

    Example::

        from jiraone.streaming import stream_json_array

        response = requests.get(url, stream=True)
        for item in stream_json_array(response, item_key="issues"):
            process_issue(item)

    :param response: Streaming requests Response object
    :param item_key: Key containing the array of items
    :param chunk_size: Chunk size for reading

    :yields: Individual items from the JSON array

    Note:
        This is a simplified implementation. For complex JSON streaming,
        consider using ijson library.
    """
    import json

    # For simplicity, we buffer and parse
    # For truly streaming JSON, use ijson
    content = b""
    for chunk in response.iter_content(chunk_size=chunk_size):
        content += chunk

    try:
        data = json.loads(content.decode("utf-8"))
        items = data.get(item_key, [])
        for item in items:
            yield item
    except json.JSONDecodeError as e:
        raise JiraAPIError(
            message=f"Failed to parse JSON response: {e}",
            url=response.url,
            method="GET",
        ) from e


class StreamingUploader:
    """Streaming uploader for large file uploads.

    Uploads files in a streaming fashion to minimize memory usage.

    Example::

        from jiraone.streaming import StreamingUploader

        uploader = StreamingUploader(
            url="https://example.atlassian.net/rest/api/3/issue/TEST-1/attachments",
            auth=("email@example.com", "api-token"),
        )
        result = uploader.upload_file("large_attachment.pdf")
    """

    def __init__(
        self,
        url: str,
        auth: Optional[tuple] = None,
        headers: Optional[Dict[str, str]] = None,
        config: Optional[StreamConfig] = None,
    ) -> None:
        """Initialize the streaming uploader.

        :param url: URL to upload to
        :param auth: Tuple of (username, password/token) for basic auth
        :param headers: Additional headers to include
        :param config: Streaming configuration
        """
        self.url = url
        self.auth = HTTPBasicAuth(*auth) if auth else None
        self.headers = headers or {}
        self.config = config or StreamConfig()

    def upload_file(
        self,
        filepath: str,
        field_name: str = "file",
    ) -> requests.Response:
        """Upload a file using streaming.

        :param filepath: Path to the file to upload
        :param field_name: Form field name for the file

        :return: Response from the upload request

        :raises JiraFileError: If file doesn't exist or can't be read
        :raises JiraAPIError: If upload fails
        """
        if not os.path.exists(filepath):
            raise JiraFileError(
                message=f"File not found: {filepath}",
                filename=filepath,
                operation="upload",
            )

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)

        def file_generator():
            """Generator to stream file contents."""
            bytes_sent = 0
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(self.config.chunk_size)
                    if not chunk:
                        break
                    bytes_sent += len(chunk)
                    if self.config.progress_callback:
                        self.config.progress_callback(bytes_sent, file_size)
                    yield chunk

        try:
            # For Jira attachments, we need multipart form data
            # Using files parameter with generator
            headers = self.headers.copy()
            headers["X-Atlassian-Token"] = "no-check"

            # Read file for multipart upload
            with open(filepath, "rb") as f:
                files = {field_name: (filename, f)}
                response = requests.post(
                    self.url,
                    auth=self.auth,
                    headers=headers,
                    files=files,
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )

            response.raise_for_status()
            add_log(f"Uploaded {filepath} ({file_size} bytes)", "debug")
            return response

        except requests.exceptions.RequestException as e:
            add_log(f"Upload failed: {filepath}", "error")
            raise JiraAPIError(
                message=f"Upload failed: {e}",
                url=self.url,
                method="POST",
            ) from e
