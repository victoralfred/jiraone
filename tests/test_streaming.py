#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the streaming module."""
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from jiraone.streaming import (
    StreamConfig,
    StreamingDownloader,
    StreamingUploader,
    ChunkedExporter,
    streaming_download,
    stream_json_array,
)
from jiraone.exceptions import JiraAPIError, JiraFileError


class TestStreamConfig:
    """Tests for StreamConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = StreamConfig()
        assert config.chunk_size == 8192
        assert config.timeout == 300
        assert config.verify_ssl is True
        assert config.progress_callback is None
        assert config.buffer_size == 65536

    def test_custom_values(self):
        """Test custom configuration values."""
        callback = lambda x, y: None
        config = StreamConfig(
            chunk_size=16384,
            timeout=600,
            verify_ssl=False,
            progress_callback=callback,
            buffer_size=131072,
        )
        assert config.chunk_size == 16384
        assert config.timeout == 600
        assert config.verify_ssl is False
        assert config.progress_callback is callback
        assert config.buffer_size == 131072


class TestStreamingDownloader:
    """Tests for StreamingDownloader class."""

    def test_init_with_defaults(self):
        """Test initialization with defaults."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        assert downloader.url == "https://example.com/file.pdf"
        assert downloader.auth is None
        assert downloader.headers == {}
        assert isinstance(downloader.config, StreamConfig)

    def test_init_with_auth(self):
        """Test initialization with authentication."""
        downloader = StreamingDownloader(
            url="https://example.com/file.pdf",
            auth=("user", "pass"),
        )
        assert downloader.auth is not None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = StreamConfig(chunk_size=16384)
        downloader = StreamingDownloader(
            url="https://example.com/file.pdf",
            config=config,
        )
        assert downloader.config.chunk_size == 16384

    def test_bytes_downloaded_initial(self):
        """Test bytes_downloaded starts at zero."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        assert downloader.bytes_downloaded == 0

    def test_total_size_initial(self):
        """Test total_size is None initially."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        assert downloader.total_size is None

    def test_progress_percent_without_total(self):
        """Test progress_percent returns None without total size."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        assert downloader.progress_percent is None

    @patch('requests.get')
    def test_stream_success(self, mock_get):
        """Test successful streaming download."""
        mock_response = Mock()
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        chunks = list(downloader.stream())

        assert len(chunks) == 2
        assert chunks[0] == b"chunk1"
        assert chunks[1] == b"chunk2"

    @patch('requests.get')
    def test_stream_with_progress_callback(self, mock_get):
        """Test streaming with progress callback."""
        mock_response = Mock()
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        callback_data = []
        config = StreamConfig(
            progress_callback=lambda bytes_read, total: callback_data.append(
                (bytes_read, total)
            )
        )
        downloader = StreamingDownloader(
            url="https://example.com/file.pdf",
            config=config,
        )
        list(downloader.stream())

        assert len(callback_data) == 1
        assert callback_data[0][1] == 1000  # Total size

    @patch('requests.get')
    def test_stream_request_error(self, mock_get):
        """Test stream handles request errors."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        with pytest.raises(JiraAPIError) as exc_info:
            list(downloader.stream())
        assert "Download failed" in str(exc_info.value)

    @patch('requests.get')
    def test_download_to_file_success(self, mock_get):
        """Test download_to_file success."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        downloader = StreamingDownloader(url="https://example.com/file.pdf")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            filepath = tmp.name

        try:
            bytes_written = downloader.download_to_file(filepath, overwrite=True)
            assert bytes_written == 7  # len(b"content")
            with open(filepath, "rb") as f:
                assert f.read() == b"content"
        finally:
            os.unlink(filepath)

    @patch('requests.get')
    def test_download_to_file_no_overwrite(self, mock_get):
        """Test download_to_file raises error when file exists and no overwrite."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            filepath = tmp.name

        try:
            with pytest.raises(JiraFileError) as exc_info:
                downloader.download_to_file(filepath, overwrite=False)
            assert "already exists" in str(exc_info.value)
        finally:
            os.unlink(filepath)

    def test_iterable(self):
        """Test downloader is iterable."""
        downloader = StreamingDownloader(url="https://example.com/file.pdf")
        assert hasattr(downloader, "__iter__")


class TestChunkedExporter:
    """Tests for ChunkedExporter class."""

    def test_init_creates_file(self):
        """Test initialization creates file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath)
            assert os.path.exists(filepath)
            exporter.close()
        finally:
            os.unlink(filepath)

    def test_init_with_headers(self):
        """Test initialization with headers writes header row."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(
                filepath=filepath,
                headers=["Name", "Value"],
            )
            exporter.close()

            with open(filepath, "r") as f:
                content = f.read()
            assert "Name,Value" in content
        finally:
            os.unlink(filepath)

    def test_write_row(self):
        """Test writing a single row."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath)
            exporter.write_row(["value1", "value2"])
            exporter.close()

            with open(filepath, "r") as f:
                content = f.read()
            assert "value1,value2" in content
        finally:
            os.unlink(filepath)

    def test_write_rows(self):
        """Test writing multiple rows."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath)
            count = exporter.write_rows([["a", "b"], ["c", "d"]])
            exporter.close()

            assert count == 2
            assert exporter.total_rows_written == 2
        finally:
            os.unlink(filepath)

    def test_write_dict_row(self):
        """Test writing a dictionary row."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(
                filepath=filepath,
                headers=["key", "value"],
            )
            exporter.write_dict_row({"key": "test", "value": "123"})
            exporter.close()

            with open(filepath, "r") as f:
                content = f.read()
            assert "test,123" in content
        finally:
            os.unlink(filepath)

    def test_file_rotation(self):
        """Test file rotation when max_rows_per_file is reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "export.csv")

            exporter = ChunkedExporter(
                filepath=filepath,
                max_rows_per_file=2,
            )
            exporter.write_row(["row1"])
            exporter.write_row(["row2"])
            exporter.write_row(["row3"])  # Should trigger rotation
            exporter.close()

            assert len(exporter.files_created) == 2

    def test_context_manager(self):
        """Test using ChunkedExporter as context manager."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            with ChunkedExporter(filepath=filepath) as exporter:
                exporter.write_row(["test"])

            # File should be closed after context
            with open(filepath, "r") as f:
                content = f.read()
            assert "test" in content
        finally:
            os.unlink(filepath)

    def test_total_rows_written(self):
        """Test total_rows_written property."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath)
            exporter.write_row(["a"])
            exporter.write_row(["b"])
            exporter.write_row(["c"])

            assert exporter.total_rows_written == 3
            exporter.close()
        finally:
            os.unlink(filepath)

    def test_flush(self):
        """Test flush method."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath)
            exporter.write_row(["test"])
            exporter.flush()  # Should not raise
            exporter.close()
        finally:
            os.unlink(filepath)

    def test_custom_delimiter(self):
        """Test custom delimiter."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            filepath = tmp.name

        try:
            exporter = ChunkedExporter(filepath=filepath, delimiter=";")
            exporter.write_row(["a", "b", "c"])
            exporter.close()

            with open(filepath, "r") as f:
                content = f.read()
            assert "a;b;c" in content
        finally:
            os.unlink(filepath)


class TestStreamingDownloadContextManager:
    """Tests for streaming_download context manager."""

    def test_context_manager_yields_downloader(self):
        """Test context manager yields StreamingDownloader."""
        with streaming_download("https://example.com/file.pdf") as downloader:
            assert isinstance(downloader, StreamingDownloader)

    def test_context_manager_with_auth(self):
        """Test context manager with auth."""
        with streaming_download(
            "https://example.com/file.pdf",
            auth=("user", "pass"),
        ) as downloader:
            assert downloader.auth is not None


class TestStreamJsonArray:
    """Tests for stream_json_array function."""

    def test_stream_items(self):
        """Test streaming items from JSON array."""
        mock_response = Mock()
        mock_response.iter_content.return_value = [
            b'{"values": [{"id": 1}, {"id": 2}]}'
        ]
        mock_response.url = "https://example.com/api"

        items = list(stream_json_array(mock_response, item_key="values"))

        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    def test_stream_invalid_json(self):
        """Test handling invalid JSON."""
        mock_response = Mock()
        mock_response.iter_content.return_value = [b"not json"]
        mock_response.url = "https://example.com/api"

        with pytest.raises(JiraAPIError) as exc_info:
            list(stream_json_array(mock_response))
        assert "Failed to parse JSON" in str(exc_info.value)

    def test_stream_empty_array(self):
        """Test streaming empty array."""
        mock_response = Mock()
        mock_response.iter_content.return_value = [b'{"values": []}']
        mock_response.url = "https://example.com/api"

        items = list(stream_json_array(mock_response, item_key="values"))
        assert len(items) == 0


class TestStreamingUploader:
    """Tests for StreamingUploader class."""

    def test_init_with_defaults(self):
        """Test initialization with defaults."""
        uploader = StreamingUploader(url="https://example.com/upload")
        assert uploader.url == "https://example.com/upload"
        assert uploader.auth is None

    def test_init_with_auth(self):
        """Test initialization with authentication."""
        uploader = StreamingUploader(
            url="https://example.com/upload",
            auth=("user", "pass"),
        )
        assert uploader.auth is not None

    def test_upload_file_not_found(self):
        """Test upload_file raises error for nonexistent file."""
        uploader = StreamingUploader(url="https://example.com/upload")
        with pytest.raises(JiraFileError) as exc_info:
            uploader.upload_file("/nonexistent/file.pdf")
        assert "File not found" in str(exc_info.value)

    @patch('requests.post')
    def test_upload_file_success(self, mock_post):
        """Test successful file upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        uploader = StreamingUploader(
            url="https://example.com/upload",
            auth=("user", "pass"),
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            filepath = tmp.name

        try:
            response = uploader.upload_file(filepath)
            assert response.status_code == 200
        finally:
            os.unlink(filepath)

    @patch('requests.post')
    def test_upload_file_request_error(self, mock_post):
        """Test upload_file handles request errors."""
        mock_post.side_effect = requests.exceptions.RequestException("Upload failed")

        uploader = StreamingUploader(url="https://example.com/upload")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            filepath = tmp.name

        try:
            with pytest.raises(JiraAPIError) as exc_info:
                uploader.upload_file(filepath)
            assert "Upload failed" in str(exc_info.value)
        finally:
            os.unlink(filepath)
