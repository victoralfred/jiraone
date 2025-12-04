#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for jiraone.file_io module."""
import os
import pytest
from unittest.mock import patch, MagicMock

from jiraone.file_io import (
    path_builder,
    file_writer,
    file_reader,
    replacement_placeholder,
)


class TestPathBuilder:
    """Tests for path_builder function."""

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        new_dir = tmp_path / "new_report_dir"
        assert not new_dir.exists()

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = path_builder("new_report_dir", "test.csv")

        assert new_dir.exists()
        assert result == str(new_dir / "test.csv")

    def test_returns_file_path(self, tmp_path):
        """Test that correct file path is returned."""
        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = path_builder("Reports", "data.csv")

        expected = str(tmp_path / "Reports" / "data.csv")
        assert result == expected

    def test_returns_directory_if_no_filename(self, tmp_path):
        """Test that directory path is returned when no filename provided."""
        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = path_builder("Reports", None)

        expected = str(tmp_path / "Reports")
        assert result == expected

    def test_custom_base_path(self, tmp_path):
        """Test using a custom base path."""
        result = path_builder("Reports", "data.csv", base_path=str(tmp_path))
        expected = str(tmp_path / "Reports" / "data.csv")
        assert result == expected


class TestFileWriter:
    """Tests for file_writer function."""

    def test_write_single_row(self, tmp_path):
        """Test writing a single row to CSV."""
        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            file_writer("test_folder", "test.csv", ["col1", "col2", "col3"], mode="w")

        file_path = tmp_path / "test_folder" / "test.csv"
        assert file_path.exists()

        content = file_path.read_text()
        assert "col1,col2,col3" in content

    def test_write_multiple_rows(self, tmp_path):
        """Test writing multiple rows to CSV."""
        rows = [["a", "b"], ["c", "d"], ["e", "f"]]

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            file_writer("test_folder", "test.csv", rows, mark="many", mode="w")

        file_path = tmp_path / "test_folder" / "test.csv"
        content = file_path.read_text()

        assert "a,b" in content
        assert "c,d" in content
        assert "e,f" in content

    def test_write_binary_content(self, tmp_path):
        """Test writing binary content."""
        binary_data = b"binary content here"

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            file_writer(
                "test_folder", "test.bin",
                data=None, mark="file",
                content=binary_data, mode="wb"
            )

        file_path = tmp_path / "test_folder" / "test.bin"
        assert file_path.exists()
        assert file_path.read_bytes() == binary_data

    def test_custom_delimiter(self, tmp_path):
        """Test using a custom delimiter."""
        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            file_writer(
                "test_folder", "test.csv",
                ["col1", "col2", "col3"],
                mode="w", delimiter=";"
            )

        file_path = tmp_path / "test_folder" / "test.csv"
        content = file_path.read_text()
        assert "col1;col2;col3" in content


class TestFileReader:
    """Tests for file_reader function."""

    def test_read_csv(self, tmp_path):
        """Test reading a CSV file."""
        # Create a test CSV file
        file_path = tmp_path / "test_folder" / "test.csv"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("a,b,c\n1,2,3\n4,5,6\n")

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = file_reader("test_folder", "test.csv")

        assert len(result) == 3
        assert result[0] == ["a", "b", "c"]
        assert result[1] == ["1", "2", "3"]
        assert result[2] == ["4", "5", "6"]

    def test_read_csv_skip_header(self, tmp_path):
        """Test reading CSV with header skip."""
        file_path = tmp_path / "test_folder" / "test.csv"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("header1,header2\ndata1,data2\n")

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = file_reader("test_folder", "test.csv", skip=True)

        assert len(result) == 1
        assert result[0] == ["data1", "data2"]

    def test_read_with_custom_delimiter(self, tmp_path):
        """Test reading with custom delimiter."""
        file_path = tmp_path / "test_folder" / "test.csv"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("a;b;c\n1;2;3\n")

        with patch("jiraone.file_io.WORK_PATH", str(tmp_path)):
            result = file_reader("test_folder", "test.csv", delimiter=";")

        assert result[0] == ["a", "b", "c"]
        assert result[1] == ["1", "2", "3"]


class TestReplacementPlaceholder:
    """Tests for replacement_placeholder function."""

    def test_single_replacement(self):
        """Test single placeholder replacement."""
        data = ["Hello <name>"]
        iterable = ["World"]
        result = replacement_placeholder("<name>", data, iterable, 0)

        assert result == ["Hello World"]

    def test_multiple_replacements(self):
        """Test multiple placeholder replacements."""
        data = ["<name> says <name> to <name>"]
        iterable = ["Alice", "hello", "Bob"]
        result = replacement_placeholder("<name>", data, iterable, 0)

        assert result == ["Alice says hello to Bob"]

    def test_replacement_in_list(self):
        """Test replacement across multiple list items."""
        data = ["First: <x>", "Second: <x>", "Third: <x>"]
        iterable = ["A", "B", "C"]
        result = replacement_placeholder("<x>", data, iterable, 0)

        assert result[0] == "First: A"
        # Only first occurrence per iteration is replaced

    def test_no_match_returns_none(self):
        """Test that no match returns None."""
        data = ["no placeholder here"]
        iterable = ["replacement"]
        result = replacement_placeholder("<missing>", data, iterable, 0)

        assert result is None
