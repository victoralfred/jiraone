#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Iterator utilities for jiraone.

This module provides iterator classes for handling pagination
and data iteration in a Pythonic way.
"""
from typing import Any, Dict, Union


class For:
    """A class to show the implementation of a 'for' loop.

    It calls the __iter__ magic method then the __next__ method
    and raises a StopIteration once it reaches the end of the loop.
    Datatype expected are list, dict, tuple, str, set or int.

    Example 1::

     from jiraone import For

     data = {"work": "home", "house": 2}
     result = For(data)
     print(list(result))
     # [{'work': 'home'}, {'house': 2}]

    Accessing dictionary index using private method `__dictionary__`

    Example 2::

      # previous expression
      print(result.__dictionary__(1))
      # {'house': 2}

    The above shows how you can call an index of a dictionary object.

    Example 3::

       from jiraone import For

       data = "Summary"
       result = For(data)
       print(list(result))
       # ['S', 'u', 'm', 'm', 'a', 'r', 'y']

    Basically you can get a list of any data structure used. For integers, it
    creates a range of those numbers.
    """

    def __init__(
        self, data: Union[list, tuple, dict, set, str, int], limit: int = 0
    ) -> None:
        """Initialize the iterator.

        :param data: The data to iterate over
        :param limit: Starting index for iteration

        :return: None
        """
        self.data = data
        if isinstance(self.data, int):
            self.data = range(1, data + 1)
        if isinstance(self.data, set):
            self.data = list(data)
        self.index = len(self.data)
        self.limit = limit

    def __iter__(self) -> Any:
        """Return the iterator object."""
        return self

    def __next__(self) -> Any:
        """Return the next item in the iteration."""
        if self.limit == self.index:
            raise StopIteration
        marker = self.limit
        self.limit += 1
        return (
            self.data[marker]
            if not isinstance(self.data, dict)
            else self.__dictionary__(marker)
        )

    def __dictionary__(self, index: int = 0) -> Dict:
        """Convert a dictionary into an item list at the given index.

        :param index: The index to retrieve

        :return: A dictionary with a single key-value pair
        """
        keys = self.data.keys()
        values = self.data.values()
        return {list(keys)[index]: list(values)[index]}
