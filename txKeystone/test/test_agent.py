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

import json
import mock
from StringIO import StringIO

from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase
from twisted.web.client import Agent, ResponseDone
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IResponse
from twisted.web.test.test_webclient import (
    FakeReactorAndConnectMixin,
    FileConsumer)
from zope.interface import implements

from txKeystone import KeystoneAgent

success_auth_response = json.dumps({
    'access': {
        'token': {
            'id': 'authToken',
            'tenant': {'id': 'tenantId'}
        }
    },
})


class DummyResponse(object):
    implements(IResponse)

    def __init__(self, code, phrase, headers, body):
        self.version = ('HTTP', 1, 1)
        self.code = code
        self.phrase = phrase
        self.headers = headers or Headers({})
        self.length = len(body)
        self._body = body

    def deliverBody(self, protocol):
        protocol.dataReceived(self._body)
        protocol.connectionLost(ResponseDone())


class KeystoneAgentTests(TestCase, FakeReactorAndConnectMixin):
    def setUp(self):
        self.agent = mock.Mock(Agent)

        self._responses = []

        def _do_response(*args, **kwargs):
            d = Deferred()
            self._responses.append(d)
            return d

        self.agent.request.side_effect = _do_response

    def respond(self, code, phrase, headers=None, body=None):
        self._responses.pop().callback(DummyResponse(code,
                                                     phrase,
                                                     headers,
                                                     body))

    def assertRequest(self, agent, method, url, headers, body):
        call = self.agent.request.mock_calls[-1][1]
        self.assertEqual(call[0], method)
        self.assertEqual(call[1], url)
        self.assertEqual(call[2], headers)

        if not body:
            #self.assertEqual(call[3], body)
            return

        bodyProducer = call[3]

        self.assertTrue(IBodyProducer.providedBy(bodyProducer))

        output = StringIO()
        consumer = FileConsumer(output)

        def _check_body(_):
            self.assertEqual(output.getvalue(), body)

        d = bodyProducer.startProducing(consumer)
        d.addCallback(_check_body)
        return d

    def test_auth_request_api_key(self):
        agent = KeystoneAgent(
            self.agent,
            'https://auth.api/v2.0/tokens',
            ('username', 'apikey'))

        agent.request('GET', 'https://compute.api')

        self.assertEqual(self.agent.request.call_count, 1)

        return self.assertRequest(
            agent,
            'POST',
            'https://auth.api/v2.0/tokens',
            Headers({'Content-Type': ['application/json']}),
            ('{"auth": {"RAX-KSKEY:apiKeyCredentials": '
             '{"username": "username", "apiKey": "apikey"}}}'))

    def test_auth_request_password(self):
        agent = KeystoneAgent(
            self.agent,
            'https://auth.api/v2.0/tokens',
            ('username', 'password'), 'password')

        agent.request('GET', 'https://compute.api')

        self.assertEqual(self.agent.request.call_count, 1)

        return self.assertRequest(
            agent,
            'POST',
            'https://auth.api/v2.0/tokens',
            Headers({'Content-Type': ['application/json']}),
            ('{"auth": {"passwordCredentials": '
             '{"username": "username", "password": "password"}}}'))

    def test_auth_success(self):
        agent = KeystoneAgent(self.agent,
                              'https://auth.api/v2.0/tokens',
                              ('username', 'apikey'))

        agent.request('GET', 'https://compute.api')
        self.respond(200, 'OK', None, success_auth_response)

        self.assertEqual(self.agent.request.call_count, 2)

        return self.assertRequest(
            agent,
            'GET',
            'https://compute.api',
            Headers({'x-tenant-id': ['tenantId'],
                     'x-auth-token': ['authToken']}),
            None)

    def test_auth_failure(self):
        def verifyError(err):
            self.assertTrue(str(err).find('Keystone authentication ' +
                                          'credentials rejected') != -1)

        agent = KeystoneAgent(self.agent,
                              'https://auth.api/v2.0/tokens',
                              ('username', 'apikey'))

        d = agent.request('GET', 'https://compute.api')
        d.addErrback(verifyError)

        self.respond(401, 'BAD', None, success_auth_response)

        self.assertEqual(self.agent.request.call_count, 1)

        return self.assertRequest(
            agent,
            'POST',
            'https://auth.api/v2.0/tokens',
            Headers({'content-type': ['application/json']}),
            None)
