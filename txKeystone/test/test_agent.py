from StringIO import StringIO

from twisted.trial.unittest import TestCase

from twisted.web.iweb import IBodyProducer
from twisted.web.client import Response

from twisted.web.test.test_webclient import (
    FakeReactorAndConnectMixin,
    FileConsumer)


from txKeystone import KeystoneAgent


class KeystoneAgentTests(TestCase, FakeReactorAndConnectMixin):
    def setUp(self):
        self.reactor = self.Reactor()
        self.agent = self.buildAgentForWrapperTest(self.reactor)

    def test_auth_request_api_key(self):
        agent = KeystoneAgent(
            self.agent,
            'https://auth.api/v2.0/tokens',
            ('username', 'apikey'))

        agent.request('GET', 'https://compute.api')

        protocol = self.protocol

        self.assertEqual(len(protocol.requests), 1)
        req, res = protocol.requests.pop()
        self.assertEqual(req.method, 'POST')
        self.assertEqual(req.uri, '/v2.0/tokens')
        self.assertTrue(IBodyProducer.providedBy(req.bodyProducer))

        output = StringIO()
        consumer = FileConsumer(output)

        def _check_body(_):
            self.assertEqual(
                output.getvalue(),
                ('{"auth": {"RAX-KSKEY:apiKeyCredentials": '
                 '{"username": "username", "apiKey": "apikey"}}}'))

        d = req.bodyProducer.startProducing(consumer)
        d.addCallback(_check_body)
        return d

    def test_auth_request_password(self):
        agent = KeystoneAgent(
            self.agent,
            'https://auth.api/v2.0/tokens',
            ('username', 'password'), 'password')

        agent.request('GET', 'https://compute.api')

        protocol = self.protocol

        self.assertEqual(len(protocol.requests), 1)
        req, res = protocol.requests.pop()
        self.assertEqual(req.method, 'POST')
        self.assertEqual(req.uri, '/v2.0/tokens')
        self.assertTrue(IBodyProducer.providedBy(req.bodyProducer))

        output = StringIO()
        consumer = FileConsumer(output)

        def _check_body(_):
            self.assertEqual(
                output.getvalue(),
                ('{"auth": {"passwordCredentials": '
                 '{"username": "username", "password": "password"}}}'))

        d = req.bodyProducer.startProducing(consumer)
        d.addCallback(_check_body)
        return d
