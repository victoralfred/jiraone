#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Jira field type definitions and utilities.

This module provides constants and utilities for working with Jira custom
and system field types.

Example::

    from jiraone.fields import FIELD_TYPES, FIELD_SEARCH_KEYS

    # Get the schema type for a cascading select field
    schema_type = FIELD_TYPES["cascadingselect"]

    # Check if a field type exists
    if "multiselect" in FIELD_TYPES:
        print("Multiselect is supported")
"""
from typing import Dict


# Custom field type schemas
FIELD_TYPES: Dict[str, str] = {
    # Standard custom field types
    "cascadingselect": "com.atlassian.jira.plugin.system.customfieldtypes:cascadingselect",
    "datepicker": "com.atlassian.jira.plugin.system.customfieldtypes:datepicker",
    "datetime": "com.atlassian.jira.plugin.system.customfieldtypes:datetime",
    "float": "com.atlassian.jira.plugin.system.customfieldtypes:float",
    "grouppicker": "com.atlassian.jira.plugin.system.customfieldtypes:grouppicker",
    "importid": "com.atlassian.jira.plugin.system.customfieldtypes:importid",
    "labels": "com.atlassian.jira.plugin.system.customfieldtypes:labels",
    "multicheckboxes": "com.atlassian.jira.plugin.system.customfieldtypes:multicheckboxes",
    "multigrouppicker": "com.atlassian.jira.plugin.system.customfieldtypes:multigrouppicker",
    "multiselect": "com.atlassian.jira.plugin.system.customfieldtypes:multiselect",
    "multiuserpicker": "com.atlassian.jira.plugin.system.customfieldtypes:multiuserpicker",
    "multiversion": "com.atlassian.jira.plugin.system.customfieldtypes:multiversion",
    "project": "com.atlassian.jira.plugin.system.customfieldtypes:project",
    "radiobuttons": "com.atlassian.jira.plugin.system.customfieldtypes:radiobuttons",
    "readonlyfield": "com.atlassian.jira.plugin.system.customfieldtypes:readonlyfield",
    "select": "com.atlassian.jira.plugin.system.customfieldtypes:select",
    "textarea": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
    "textfield": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
    "url": "com.atlassian.jira.plugin.system.customfieldtypes:url",
    "userpicker": "com.atlassian.jira.plugin.system.customfieldtypes:userpicker",
    "version": "com.atlassian.jira.plugin.system.customfieldtypes:version",
    # Agile field types
    "sprint": "com.pyxis.greenhopper.jira:gh-sprint",
    "epiclink": "com.pyxis.greenhopper.jira:gh-epic-link",
    "Epic Status": "com.pyxis.greenhopper.jira:gh-epic-status",
    "Epic Name": "com.pyxis.greenhopper.jira:gh-epic-label",
    # System field aliases
    "components": "components",
    "fixversions": "fixVersions",
    "originalestimate": "timeoriginalestimate",
    "timetracking": "timetracking",
    "reporter": "reporter",
    "assignee": "assignee",
    "description": "description",
    "versions": "versions",
}

# Field search key schemas (used for custom field configuration)
FIELD_SEARCH_KEYS: Dict[str, str] = {
    "cascadingselectsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:cascadingselectsearcher",
    "daterange": "com.atlassian.jira.plugin.system.customfieldtypes:daterange",
    "datetimerange": "com.atlassian.jira.plugin.system.customfieldtypes:datetimerange",
    "exactnumber": "com.atlassian.jira.plugin.system.customfieldtypes:exactnumber",
    "exacttextsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:exacttextsearcher",
    "grouppickersearcher": "com.atlassian.jira.plugin.system.customfieldtypes:grouppickersearcher",
    "labelsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:labelsearcher",
    "multiselectsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:multiselectsearcher",
    "numberrange": "com.atlassian.jira.plugin.system.customfieldtypes:numberrange",
    "projectsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:projectsearcher",
    "textsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
    "userpickergroupsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:userpickergroupsearcher",
    "versionsearcher": "com.atlassian.jira.plugin.system.customfieldtypes:versionsearcher",
}


def get_field_type(name: str) -> str:
    """Get the schema type for a field by its short name.

    :param name: Short name of the field type (e.g., "multiselect")
    :return: Full schema type string
    :raises KeyError: If the field type is not found

    Example::

        schema = get_field_type("multiselect")
        # Returns: "com.atlassian.jira.plugin.system.customfieldtypes:multiselect"
    """
    return FIELD_TYPES[name]


def get_search_key(name: str) -> str:
    """Get the search key schema for a field searcher.

    :param name: Short name of the searcher (e.g., "textsearcher")
    :return: Full search key schema string
    :raises KeyError: If the search key is not found

    Example::

        key = get_search_key("textsearcher")
        # Returns: "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher"
    """
    return FIELD_SEARCH_KEYS[name]


def is_custom_field_id(field_id: str) -> bool:
    """Check if a field ID represents a custom field.

    :param field_id: The field ID to check
    :return: True if it's a custom field ID

    Example::

        is_custom_field_id("customfield_10001")  # True
        is_custom_field_id("summary")  # False
    """
    return field_id.startswith("customfield_")


def extract_custom_field_number(field_id: str) -> int:
    """Extract the numeric ID from a custom field ID.

    :param field_id: The custom field ID (e.g., "customfield_10001")
    :return: The numeric ID (e.g., 10001)
    :raises ValueError: If the field ID is not a valid custom field ID

    Example::

        num = extract_custom_field_number("customfield_10001")
        # Returns: 10001
    """
    if not is_custom_field_id(field_id):
        raise ValueError(f"Not a valid custom field ID: {field_id}")
    return int(field_id.replace("customfield_", ""))
