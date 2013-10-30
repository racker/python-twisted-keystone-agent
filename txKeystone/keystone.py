# Copyright 2012 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import httplib

try:
    import simplejson as json
except:
    import json

from cStringIO import StringIO
from Queue import Queue
from twisted.internet.defer import Deferred, succeed, fail
from twisted.internet.protocol import Protocol
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.python import log


class KeystoneAgent(object):
    """
    Fetches and inserts X-Auth-Token and X-Tenant-Id headers into requests
    made using this agent.

    @cvar auth_headers: Dictionary in the form
                        ("X-Tenant-Id": "id", "X-Auth-Token": "token")
                        containing current authentication header data.
    @cvar MAX_RETRIES: Maximum number of connection attempts to make
                       before failing.
    """
    MAX_RETRIES = 3

    NOT_AUTHENTICATED = 1
    AUTHENTICATING = 2
    AUTHENTICATED = 3

    def __init__(self, agent, auth_url, auth_cred, auth_type='api_key',
                 verbose=False):
        """
        @param agent: Agent for use by this class
        @param auth_url: URL to use for Keystone authentication
        @param auth_cred: A tuple in the form ("username", "api_key")
                          or ("username", "password")
        @param auth_type: Either api_key or password, depending on what
                          you want to use to authenticate.
        @param verbose: Enable verbose logging, False by default.
        """
        self.agent = agent
        self.auth_url = auth_url
        self.auth_cred = auth_cred
        self.auth_type = auth_type
        self.verbose = verbose

        self.auth_headers = {"X-Auth-Token": None, "X-Tenant-Id": None}

        self._state = self.NOT_AUTHENTICATED
        self._headers_requests = Queue()

    def msg(self, msg, **kwargs):
        if self.verbose:
            log.msg(format=msg, system="KeystoneAgent", **kwargs)

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        @param method: The request method to send ("GET", "POST", etc.)
        @type method: C{str}
        @param uri: The request URI to send
        @type uri: C{str}
        @param headers: The request headers to send
        @type headers: L{Headers}
        @param bodyProducer: An object which will produce the request body or,
        if the request body is to be empty, None.
        @type bodyProducer: L{IBodyProducer} provider
        @return: A L{Deferred} which fires with the result of the request (a
        Response instance), or fails if there is a problem setting up a
        connection over which to issue the request.
        """
        self.msg("request (%(method)s): %(uri)s", method=method, uri=uri)

        return self._request(method,
                             uri,
                             headers=headers,
                             bodyProducer=bodyProducer)

    def _request(self, method, uri, headers=None, bodyProducer=None, depth=0):
        self.msg("_request depth %(depth)s (%(method)s): %(uri)s",
                 method=method, uri=uri, depth=depth)

        if headers is None:
            headers = Headers()

        if depth == self.MAX_RETRIES:
            return fail(AuthenticationError("Authentication headers"
                                            "rejected after max retries"))

        def _handleResponse(response, method=method, uri=uri, headers=headers):
            self.msg("_handleResponse (%(method)s): %(uri)s",
                     method=method, uri=uri, depth=depth)

            if response.code == httplib.UNAUTHORIZED:
                # The auth headers were not accepted,
                # force an update and # recurse
                self.auth_headers = {"X-Auth-Token": None,
                                     "X-Tenant-Id": None}
                self._state = self.NOT_AUTHENTICATED

                return self._request(method,
                                     uri,
                                     headers=headers,
                                     bodyProducer=bodyProducer,
                                     depth=depth + 1)
            else:
                #The auth headers were accepted, return the response
                return response

        def _makeRequest(auth_headers):
            self.msg("_makeRequest %(auth_headers)s (%(method)s): %(uri)s",
                     auth_headers=auth_headers, method=method, uri=uri)

            for header, value in auth_headers.items():
                headers.setRawHeaders(header, [value])

            req = self.agent.request(method,
                                     uri,
                                     headers,
                                     bodyProducer)

            req.addCallback(_handleResponse)
            return req

        # Asynchronously get the auth headers,
        # then make the request using them
        d = self._getAuthHeaders()
        d.addCallback(_makeRequest)
        return d

    def _getAuthRequestBodyProducer(self):
        if self.auth_type == "password":
            auth_type = "passwordCredentials"
            key_name = "password"
        else:
            auth_type = "RAX-KSKEY:apiKeyCredentials"
            key_name = "apiKey"

        auth_dict = {"auth":
                     {auth_type:
                      {"username": self.auth_cred[0],
                       key_name: self.auth_cred[1]}}}

        return FileBodyProducer(StringIO(json.dumps(auth_dict)))

    def getAuthHeaders(self):
        return self._getAuthHeaders()

    def _getAuthHeaders(self):
        """
        Get authentication headers. If we have valid header data already,
        they immediately return it.
        If not, then get new authentication data. If we are currently in
        the process of getting the
        header data, put this request into a queue to be handled when the
        data are received.

        @returns: A deferred that will eventually be called back with the
                  header data
        """
        def _handleAuthBody(body):
            self.msg("_handleAuthBody: %(body)s", body=body)

            try:
                body_parsed = json.loads(body)
                access_token = body_parsed['access']['token']

                tenant_id = access_token['tenant']['id'].encode('ascii')
                auth_token = access_token['id'].encode('ascii')

                self.auth_headers["X-Tenant-Id"] = tenant_id
                self.auth_headers["X-Auth-Token"] = auth_token

                self._state = self.AUTHENTICATED

                self.msg("_handleAuthHeaders: found token %(token)s"
                         " tenant id %(tenant_id)s",
                         token=self.auth_headers["X-Auth-Token"],
                         tenant_id=self.auth_headers["X-Tenant-Id"])

                # Callback all queued auth headers requests
                while not self._headers_requests.empty():
                    self._headers_requests.get().callback(self.auth_headers)

            except ValueError:
                # We received a bad response
                return fail(MalformedJSONError("Malformed keystone"
                                               " response received."))

        def _handleAuthResponse(response):
            if response.code == httplib.OK:
                self.msg("_handleAuthResponse: %(response)s accepted",
                         response=response)
                body = Deferred()
                response.deliverBody(StringIOReceiver(body))
                body.addCallback(_handleAuthBody)
                return body
            else:
                self.msg("_handleAuthResponse: %(response)s rejected",
                         response=response)
                return fail(
                    KeystoneAuthenticationError("Keystone"
                                                " authentication credentials"
                                                " rejected"))

        self.msg("_getAuthHeaders: state is %(state)s", state=self._state)

        if self._state == self.AUTHENTICATED:
            # We are authenticated, immediately succeed with the current
            # auth headers
            self.msg("_getAuthHeaders: succeed with %(headers)s",
                     headers=self.auth_headers)

            return succeed(self.auth_headers)
        elif (self._state == self.NOT_AUTHENTICATED or
              self._state == self.AUTHENTICATING):
            # We cannot satisfy the auth header request immediately,
            # put it in a queue
            self.msg("_getAuthHeaders: defer, place in queue")
            auth_headers_deferred = Deferred()
            self._headers_requests.put(auth_headers_deferred)

            if self._state == self.NOT_AUTHENTICATED:
                self.msg("_getAuthHeaders: not authenticated, start"
                         " authentication process")
                # We are not authenticated, and not in the process of
                # authenticating.
                # Set our state to AUTHENTICATING and begin the
                # authentication process
                self._state = self.AUTHENTICATING

                d = self.agent.request('POST',
                                       self.auth_url,
                                       Headers({
                                           "Content-type": ["application/json"]
                                       }),
                                       self._getAuthRequestBodyProducer())
                d.addCallback(_handleAuthResponse)
                d.addErrback(auth_headers_deferred.errback)

            return auth_headers_deferred
        else:
            # Bad state, fail
            return fail(RuntimeError("Invalid state encountered."))


class AuthenticationError(Exception):
    pass


class KeystoneAuthenticationError(AuthenticationError):
    pass


class MalformedJSONError(Exception):
    pass


class StringIOReceiver(Protocol):
    """
    A protocol to aggregate chunked data as it is received, and fire a
    callback with the aggregated data when the connection is closed.
    """
    def __init__(self, finished):
        """
        @param finished: Deferred to fire when all data have been
                         aggregated.
        """
        self.buffer = StringIO()
        self.finished = finished

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        self.finished.callback(self.buffer.getvalue())
