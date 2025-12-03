#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Authentication and credential management for Jira API.

This module provides classes for handling authentication to Jira instances,
supporting both basic authentication and OAuth 2.0 3LO.
"""
import json
import random
import string
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from jiraone.exceptions import JiraOneErrors
from jiraone.jira_logs import add_log


class Credentials:
    """Handles authentication to Jira instances.

    Supports basic authentication (username/API token) and OAuth 2.0 3LO.

    Attributes:
        auth_request: The authentication request object for basic auth.
        headers: HTTP headers to include in requests.
        api: Whether to use API version 3 (True) or latest (False).
        auth2_0: OAuth 2.0 token data as JSON string.
        base_url: The base URL of the Jira instance.
        session: The requests session for HTTP operations.
        instance_name: The name of the connected instance (OAuth only).
    """

    auth_request: Optional[HTTPBasicAuth] = None
    headers: Optional[dict] = None
    api: bool = True
    auth2_0: Optional[str] = None

    def __init__(
        self,
        user: str = None,
        password: str = None,
        url: str = None,
        oauth: dict = None,
        session: Any = None,
    ) -> None:
        """Initialize credentials for Jira authentication.

        .. versionadded:: 0.6.2

        oauth - Allows the ability to use Atlassian OAuth 2.0 3LO to
                authenticate to Jira. It supports various scopes configured from
                your `Developer Console`_

        session - Provides a means to access the request session.

        save_oauth - Is a property value which provides a dictionary
        object of the current oauth token.

        instance_name - Is an attribute of the connected instance using OAuth.
        Accessing this attribute when OAuth isn't use returns ``None``.

        :param user: A username or email address
        :param password: A user password or API token
        :param url: A server url or cloud instance url
        :param oauth: An OAuth authentication request.
        :param session: Creates a context session

        .. _Developer Console: https://developer.atlassian.com/console/myapps/

        :return: None
        """
        self.base_url = url
        self.user = user
        self.password = password
        self.oauth = oauth
        self.instance_name = None

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

        if self.user is not None and self.password is not None:
            self.token_session(self.user, self.password)
        elif oauth is not None:
            self.oauth_session(self.oauth)

    def oauth_session(self, oauth: dict) -> None:
        """Initialize a session using OAuth 2.0 3LO.

        This method implements the Atlassian OAuth 2.0 3LO implementation.
        To reissue token, this method uses a refresh token session.
        This is possible, if the scope in the ``callback_url``
        contains ``offline_access``.

        .. code-block:: python

           client = {
               "client_id": "JixkXXX",
               "client_secret": "KmnlXXXX",
               "name": "nexusfive",
               "callback_url": "https://auth.atlassian.com/XXXXX"
           }

        A typical client object should look like the above.
        Which is passed to the ``LOGIN`` initializer as below.
        The ``name`` key is needed to specifically target an instance,
        but it is optional if you have multiple instances that your app is
        connected to. The ``client_id``, ``client_secret``
        and ``callback_url`` are mandatory.

        .. code-block:: python

           from jiraone import LOGIN

           # previous expression
           LOGIN(oauth=client)

        To store and reuse the oauth token, you will need to call the
        property value. This object is a string which can be stored
        to a database and pulled as a variable.

        .. code-block:: python

           #  Example for storing the OAuth token
           dumps = LOGIN.save_oauth # this is a property value which contains a
           # dict of tokens in strings
           # As long as a handshake has been allowed with OAuth,
           # the above should exist.
           LOGIN.save_oauth = f"{json.dumps(dumps)}"
           # with the above string, you can easily save your
           # OAuth tokens into a DB or file.
           # Please note that when you initialize the oauth method,
           # you do not need to set
           # The property variable, as it will be set automatically
           # after initialization.
           # But you can assign other string objects to it or make a call to it.


        :param oauth: A dictionary containing the client and secret
                     information and any other client information that
                     can be represented within the data structure.

        :return: None
        """
        if not isinstance(oauth, dict):
            add_log("Wrong data type received for the oauth argument.", "error")
            raise JiraOneErrors(
                "wrong",
                "Excepting a dictionary object got {} instead.".format(type(oauth)),
            )
        if (
            "client_id" not in oauth
            or "client_secret" not in oauth
            or "callback_url" not in oauth
        ):
            add_log(
                "You seem to be missing a key or keys in your oauth argument.",
                "debug",
            )
            raise JiraOneErrors(
                "value",
                "You seem to be missing some vital "
                "keys in your request."
                "Please check your oauth supplied "
                "data that all keys are present.",
            )
        tokens = {}
        oauth_data = {
            "token_url": "https://auth.atlassian.com/oauth/token",
            "cloud_url": "https://api.atlassian.com/oauth/token/accessible-resources",
            "base_url": "https://api.atlassian.com/ex/jira/{cloud}",
        }

        def token_update(token) -> None:
            """Updates the token to environment variable."""
            self.session.auth = token
            self.auth2_0 = f"{json.dumps(token)}"

        def get_cloud_id():
            """Retrieve the cloud id of connected instance."""
            cloud_id = requests.get(
                oauth_data["cloud_url"], headers=self.headers
            ).json()
            for ids in cloud_id:
                if ids["name"] == oauth.get("name"):
                    self.instance_name = ids["name"]
                    # Import LOGIN here to avoid circular imports
                    from jiraone.credentials import LOGIN
                    LOGIN.base_url = oauth_data.get("base_url").format(cloud=ids["id"])
                else:
                    self.instance_name = cloud_id[0]["name"]
                    from jiraone.credentials import LOGIN
                    LOGIN.base_url = oauth_data.get("base_url").format(
                        cloud=cloud_id[0]["id"]
                    )
            from jiraone.credentials import LOGIN
            tokens.update({"base_url": LOGIN.base_url, "ins_name": self.instance_name})

        if self.auth2_0:
            sess = json.loads(self.auth2_0)
            oauth_data.update({"base_url": sess.pop("base_url")})
            self.instance_name = sess.pop("ins_name")
            tokens.update(sess)
            body = {
                "grant_type": "refresh_token",
                "client_id": oauth.get("client_id"),
                "client_secret": oauth.get("client_secret"),
                "refresh_token": tokens.get("refresh_token"),
            }
            get_token = requests.post(
                oauth_data["token_url"], json=body, headers=self.headers
            )
            if get_token.status_code < 300:
                access_token = get_token.json()["access_token"]
                refresh = get_token.json()["refresh_token"]
                expires = get_token.json()["expires_in"]
                scope = get_token.json()["scope"]
                token_type = get_token.json()["token_type"]
                extra = {"type": token_type, "token": access_token}
                tokens.update(
                    {
                        "access_token": access_token,
                        "expires_in": expires,
                        "scope": scope,
                        "refresh_token": refresh,
                    }
                )
                self.__token_only_session__(extra)
                get_cloud_id()
            else:
                add_log(
                    "Token refresh has failed to revalidate. "
                    "Reason [{} - {}]".format(
                        get_token.reason, json.loads(get_token.content)
                    ),
                    "debug",
                )
                raise JiraOneErrors(
                    "login",
                    "Refreshing token failed with code {}".format(
                        get_token.status_code
                    ),
                )

        def generate_state(i):
            """Generates a random key for state variable."""
            char = string.ascii_lowercase
            return "".join(random.choice(char) for _ in range(i))

        def validate_uri(uri) -> bool:
            """Return true or false for a sanitize version of the input url"""
            import urllib.parse

            check_url = oauth.get("callback_url").split("&")
            hostname = None
            for url in check_url:
                if url.startswith("redirect_uri"):
                    hostname = urllib.parse.unquote(url.split("=")[1])
            return hostname == uri

        state = generate_state(12)
        if tokens:
            from jiraone.credentials import LOGIN
            LOGIN.base_url = oauth_data.get("base_url")
        if not tokens:
            # add an offline_access to the scope, so we can get a refresh token
            call_back = oauth.get("callback_url").replace(
                "scope=", "scope=offline_access%20", 1
            )
            oauth.update({"callback_url": call_back})
            callback = oauth.get("callback_url").format(YOUR_USER_BOUND_VALUE=state)
            print("Please click or copy the link into your browser and hit Enter!")
            print(callback)
            redirect_url = input("Enter the redirect url: \n")
            # Check if the supplied url is true to the one
            # which exist in callback_url
            validate_url = validate_uri(redirect_url.split("?")[0].rstrip("/"))
            assert (
                validate_url is True
            ), "Your URL seems invalid as it cannot be validated."
            code = redirect_url.split("?")[1].split("&")[1].split("=")[-1]
            body = {
                "grant_type": "authorization_code",
                "client_id": oauth.get("client_id"),
                "client_secret": oauth.get("client_secret"),
                "code": code,
                "redirect_uri": redirect_url,
            }
            get_token = requests.post(
                oauth_data["token_url"], json=body, headers=self.headers
            )
            if get_token.status_code < 300:
                access_token = get_token.json()["access_token"]
                refresh = get_token.json()["refresh_token"]
                expires = get_token.json()["expires_in"]
                scope = get_token.json()["scope"]
                token_type = get_token.json()["token_type"]
                extra = {"type": token_type, "token": access_token}
                tokens.update(
                    {
                        "access_token": access_token,
                        "expires_in": expires,
                        "scope": scope,
                        "token_type": token_type,
                        "refresh_token": refresh,
                    }
                )
                self.__token_only_session__(extra)
                get_cloud_id()
            else:
                add_log(
                    "The connection using OAuth was unable to connect, please "
                    "check your client key or client secret. "
                    "Reason [{} - {}]".format(
                        get_token.reason, json.loads(get_token.content)
                    ),
                    "debug",
                )
                raise JiraOneErrors(
                    "login", "Could not establish the OAuth connection."
                )

        print("Connected to instance:", self.instance_name)
        token_update(tokens)

    @property
    def save_oauth(self) -> str:
        """Defines the OAuth data to save."""
        return self.auth2_0

    @save_oauth.setter
    def save_oauth(self, oauth: Any) -> None:
        """Sets the OAuth data."""
        self.auth2_0 = oauth

    def __token_only_session__(self, token: dict) -> None:
        """Creates a token bearer session.

        :param token: A dict containing token info.
        :return: None
        """
        self.headers = {"Content-Type": "application/json"}
        self.headers.update(
            {"Authorization": "{} {}".format(token["type"], token["token"])}
        )

    def token_session(
        self,
        email: str = None,
        token: str = None,
        sess: str = None,
        _type: str = "Bearer",
    ) -> None:
        """Initialize a session for HTTP requests.

        .. versionadded:: 0.7.1

        _type - Datatype(string) - Allows a change of the Authorization type

        .. versionadded:: 0.6.5

        sess - Datatype(string) - Allows the use of an Authorization header

        :param email: An email address or username
        :param token: An API token or user password
        :param sess: Triggers an Authorization bearer session
        :param _type: An acceptable Authorization type e.g. Bearer or JWT

        :return: None
        """
        if sess is None:
            self.auth_request = HTTPBasicAuth(email, token)
            self.headers = {"Content-Type": "application/json"}
        else:
            from jiraone.credentials import LOGIN
            if LOGIN.base_url is None:
                raise JiraOneErrors(
                    "value",
                    "Please include a connecting "
                    "base URL by declaring "
                    " LOGIN.base_url "
                    '= "https://yourinstance.atlassian.net"',
                )
            extra = {"type": _type, "token": sess}
            self.__token_only_session__(extra)

    def get(
        self, url: str, *args, payload: dict = None, **kwargs
    ) -> requests.Response:
        """Make a GET request.

        :param url: A valid URL
        :param args: Additional arguments if any
        :param payload: A JSON data representation
        :param kwargs: Additional keyword arguments to ``requests`` module

        :return: An HTTP response
        """
        response = requests.get(
            url,
            *args,
            auth=self.auth_request,
            json=payload,
            headers=self.headers,
            **kwargs,
        )
        return response

    def post(
        self, url: str, *args: Any, payload: dict = None, **kwargs
    ) -> requests.Response:
        """Make a POST request.

        :param url: A valid URL
        :param args: Additional arguments if any
        :param payload: A JSON data representation
        :param kwargs: Additional keyword arguments to ``requests`` module

        :return: An HTTP response
        """
        response = requests.post(
            url,
            *args,
            auth=self.auth_request,
            json=payload,
            headers=self.headers,
            **kwargs,
        )
        return response

    def put(
        self, url: str, *args, payload: dict = None, **kwargs
    ) -> requests.Response:
        """Make a PUT request.

        :param url: A valid URL
        :param args: Additional arguments if any
        :param payload: A JSON data representation
        :param kwargs: Additional keyword arguments to ``requests`` module

        :return: An HTTP response
        """
        response = requests.put(
            url,
            *args,
            auth=self.auth_request,
            json=payload,
            headers=self.headers,
            **kwargs,
        )
        return response

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make a DELETE request.

        :param url: A valid URL
        :param kwargs: Additional keyword arguments to ``requests`` module

        :return: An HTTP response
        """
        response = requests.delete(
            url, auth=self.auth_request, headers=self.headers, **kwargs
        )
        return response

    def custom_method(self, *args, **kwargs) -> requests.Response:
        """Make a custom HTTP request.

        .. code-block:: python

           import jiraone
           # previous login expression
           req = jiraone.LOGIN.custom_method('GET', 'https://nexusfive.atlassian.net')
           print(req)
           # <Response [200]>

        :param args: The HTTP method type e.g. PUT, PATCH, DELETE etc
                    Also, includes the URL that needs to be queried.
        :param kwargs: Additional keyword arguments to ``requests`` module
                     For example::
                       json={"file": content}
                       data={"file": content}

        :return: An HTTP response
        """
        response = requests.request(
            *args, auth=self.auth_request, headers=self.headers, **kwargs
        )
        return response

    @staticmethod
    def from_jira(obj: Any) -> Any:
        """Perform login initialization from a ``JIRA`` object.

        The authentication looks into basic auth from the ``jira`` python
        package. It returns the same JIRA object after authentication happens,
        so you can easily access all the authenticated instances of both
        ``jira`` and ``jiraone`` packages.

        Example 1::

         from jira import JIRA
         from jiraone import LOGIN, endpoint

         my_jira = JIRA(server="https://nexusfive.atlassian.net",
                 basic_auth=("prince@example.com",
                 "MXKSlsXXXXX"))
         LOGIN.from_jira(my_jira)
         print(LOGIN.get(endpoint.myself()))
         # response
         # <Response [200]>


        You can assign a variable to the jiraone :meth:`LOGIN.from_jira`
        and continue to use both ``jira`` and ``jiraone`` packages
        simultaneously.

        Example 2::

         from jira import JIRA
         from jiraone import LOGIN, PROJECT

         jiras = JIRA(server="https://nexusfive.atlassian.net",
                 basic_auth=("prince@example.com",
                 "MXKSlsXXXXX"))
         my_jira = LOGIN.from_jira(jiras)
         # Making a request to JIRA's methods
         print(my_jira.myself())
         # response
         # {'self': 'https://example.atlassian.net/rest/api/2/user?
         #            accountId=557058:xxx',
         #           'accountId': '557058:xxx'}
         # Making a request to jiraone's methods
         jql = "project = CT ORDER BY Created DESC"
         print(PROJECT.issue_count(jql))
         # response
         # {'count': 18230, 'max_page': 18}

        :param obj: A call to a ``JIRA`` Interface
        :return: JIRA object
        """
        import sys
        try:
            if hasattr(obj, "_session"):
                if obj._session.auth:
                    auth = {
                        "user": obj._session.auth[0],
                        "password": obj._session.auth[1],
                        "url": obj._options["server"],
                    }
                    from jiraone.credentials import LOGIN
                    LOGIN(**auth)
                    return obj
                else:
                    sys.exit(
                        "Unable to read other values within the ``JIRA``"
                        " object. Authentication cannot proceed further."
                    )
            else:
                sys.exit(
                    "Could not detect a `JIRA` object from the command."
                    " Please check that you have the `jira` python package "
                    "installed."
                )
        except Exception as err:
            raise JiraOneErrors(
                "wrong",
                "An unknown exception has occurred Other errors: " f" {err}.",
            ) from err


class InitProcess(Credentials):
    """Login initializer that inherits from Credentials.

    Object values are entered directly when called because of the __call__
    dunder method.
    """

    def __init__(
        self, user=None, password=None, url=None, oauth=None, session=None
    ) -> None:
        """Initialize the login process.

        .. versionadded:: 0.6.2

        oauth argument added to support OAuth 2.0

        session argument added to create a session context

        :param user: A username or email address
        :param password: A password or user API token
        :param url: A valid URL
        :param oauth: An oAuth session
        :param session: Creates a context session

        :return: None
        """
        super().__init__(
            user=user, password=password, url=url, oauth=oauth, session=session
        )

    def __call__(self, *args, **kwargs):
        """Help to make our class callable."""
        return self.__init__(*args, **kwargs)


# Global login instance
LOGIN = InitProcess()
