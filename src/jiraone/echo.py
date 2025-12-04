#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pretty printing utilities for jiraone.

This module provides a wrapper around Python's PrettyPrinter for
formatting output in a readable way.
"""
from pprint import PrettyPrinter
from typing import Any


class Echo(PrettyPrinter):
    """A class used to inherit from PrettyPrinter.

    Provides formatted output for complex data structures.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Inherit from the parent PrettyPrinter.

        :param args: positional arguments
        :param kwargs: additional arguments

        :return: None
        """
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Makes our class callable."""
        return self.__init__(*args, **kwargs)

    def echo(self, raw: Any) -> None:
        """Print the formatted representation of object on stream.

        Followed by a newline.

        :param raw: Any object data

        :return: None
        """
        return self.pprint(object=raw)


def echo(obj: Any) -> Any:
    """Call the Echo class to pretty print an object.

    :param obj: Any data type to process

    :return: Any
    """
    e = Echo()
    return e.echo(raw=obj)
