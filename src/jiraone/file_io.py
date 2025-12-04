#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""File I/O utilities for jiraone.

This module provides utilities for reading and writing files,
building paths, and handling CSV data.

Example::

    from jiraone.file_io import path_builder, file_writer, file_reader

    # Build a path for a report file
    file_path = path_builder("Reports", "my_report.csv")

    # Write data to CSV
    file_writer("Reports", "my_report.csv", ["col1", "col2", "col3"])

    # Read data from CSV
    data = file_reader("Reports", "my_report.csv")
"""
import csv
import os
from platform import system
from typing import Any, Iterable, List, Optional, Union

from jiraone.jira_logs import add_log, WORK_PATH


def path_builder(
    path: str = "Report",
    file_name: Optional[str] = None,
    base_path: Optional[str] = None,
) -> str:
    """Build a directory path and file path.

    Creates the directory if it doesn't exist and returns the full file path.

    :param path: Relative path for the directory (default: "Report")
    :param file_name: Name of the file to create
    :param base_path: Base path to use (default: WORK_PATH)
    :return: Full path to the file

    Example::

        # Create path for a report
        file_path = path_builder("Reports", "users.csv")
        # Returns: "/current/dir/Reports/users.csv"

        # With custom base path
        file_path = path_builder("data", "export.csv", base_path="/tmp")
        # Returns: "/tmp/data/export.csv"
    """
    base = base_path if base_path is not None else WORK_PATH
    base_dir = os.path.join(base, path)

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        add_log(f"Building Path {path}", "info")

    if file_name is None:
        return base_dir

    return os.path.join(base_dir, file_name)


def file_writer(
    folder: str = WORK_PATH,
    file_name: Optional[str] = None,
    data: Optional[Iterable[Any]] = None,
    mark: str = "single",
    mode: str = "a+",
    content: Optional[Union[str, bytes]] = None,
    delimiter: str = ",",
    encoding: str = "utf-8",
    errors: str = "replace",
) -> None:
    """Write data to a CSV file or binary file.

    :param folder: Path to the folder
    :param file_name: Name of the file to create
    :param data: Iterable data to write (for CSV)
    :param mark: Write mode - "single" for one row, "many" for multiple rows,
                 "file" for raw content
    :param mode: File mode ("a", "w", "a+", "w+", "wb")
    :param content: Raw content to write when mark="file"
    :param delimiter: CSV delimiter (default: ",")
    :param encoding: File encoding (default: "utf-8")
    :param errors: Error handling mode (default: "replace")

    Example::

        # Write a single row
        file_writer("Reports", "data.csv", ["name", "email", "role"])

        # Write multiple rows
        rows = [["Alice", "alice@example.com"], ["Bob", "bob@example.com"]]
        file_writer("Reports", "data.csv", rows, mark="many")

        # Write binary content
        file_writer("Downloads", "file.bin", mark="file",
                    content=binary_data, mode="wb")
    """
    file = path_builder(path=folder, file_name=file_name)

    # Determine file open mode based on OS and content type
    if system() == "Windows" and mark != "file":
        file_handle = open(
            file, mode, encoding=encoding, newline="", errors=errors
        )
    elif isinstance(content, bytes):
        file_handle = open(file, mode)
    else:
        file_handle = open(file, mode, encoding=encoding, errors=errors)

    with file_handle as f:
        if mark == "file":
            f.write(content)
        else:
            writer = csv.writer(f, delimiter=delimiter)
            if mark == "single":
                writer.writerow(data)
            elif mark == "many":
                writer.writerows(data)

        add_log(f"Writing to file {file_name}", "info")


def file_reader(
    folder: str = WORK_PATH,
    file_name: Optional[str] = None,
    mode: str = "r",
    skip: bool = False,
    content: bool = False,
    delimiter: str = ",",
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Union[List[List[str]], str, bytes]:
    """Read data from a CSV file or binary file.

    :param folder: Path to the folder
    :param file_name: Name of the file to read
    :param mode: File mode ("r" for text, "rb" for binary)
    :param skip: Skip the header row if True
    :param content: Read raw content if True, CSV otherwise
    :param delimiter: CSV delimiter (default: ",")
    :param encoding: File encoding (default: "utf-8")
    :param errors: Error handling mode (default: "replace")
    :return: List of rows for CSV, or string/bytes for raw content

    Example::

        # Read CSV data
        data = file_reader("Reports", "data.csv")
        for row in data:
            print(row)

        # Read CSV without header
        data = file_reader("Reports", "data.csv", skip=True)

        # Read binary file
        binary = file_reader("Downloads", "file.bin", mode="rb", content=True)
    """
    file = path_builder(path=folder, file_name=file_name)

    # Determine file open mode based on OS and content type
    if system() == "Windows" and not content:
        file_handle = open(
            file, mode, encoding=encoding, newline="", errors=errors
        )
    else:
        file_handle = open(file, mode)

    with file_handle as f:
        if content:
            data = f.read()
            if encoding and mode != "rb":
                data = data.encode(encoding)
            add_log(f"Read file {file_name}", "info")
            return data

        reader = csv.reader(f, delimiter=delimiter)
        if skip:
            next(reader, None)

        result = [row for row in reader]
        add_log(f"Read file {file_name}", "info")
        return result


def replacement_placeholder(
    string: str,
    data: List[str],
    iterable: List[str],
    row: int = 2,
) -> Optional[List[str]]:
    """Replace multiple occurrences of a placeholder in strings.

    :param string: The placeholder string to replace
    :param data: List of strings containing the placeholder
    :param iterable: List of replacement values
    :param row: Index of the row to check for placeholder
    :return: List of strings with replacements made

    Example::

        hold = ["Hello", "John doe", "Post mortem"]
        text = ["<name> <name>, welcome to the <name>"]
        result = replacement_placeholder("<name>", text, hold, 0)
        # result: ["Hello John doe, welcome to the Post mortem"]
    """
    result = None
    length = len(iterable)

    for count, _ in enumerate(iterable):
        if count == 0:
            if string in data[row]:
                result = [
                    line.replace(string, iterable[count], 1)
                    for line in data
                ]
        elif count > 0 and result is not None:
            if string in result[row]:
                result = [
                    line.replace(string, iterable[count], 1)
                    for line in result
                ]

        if count >= length:
            break

    return result
