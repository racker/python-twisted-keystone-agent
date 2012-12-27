import json

from twisted.python.failure import Failure
from twisted.internet.defer import succeed, fail
from twisted.web.http_headers import Headers

from treq import json_content
from treq.client import HTTPClient


class KeystoneError(Exception):
    def __init__(self, code, body):
        self.code = code
        self.body = body
        Exception.__init__(self, 'code={0}, body={1}'.format(self.code, self.body))


class KeystoneAdminRequired(Exception):
    def __init__(self, method, admin_role):
        Exception.__init__(self, '{0} requires role of {1!r}'.format(
            method, admin_role
        ))


def admin_required(method_name):
    def f(self, *args, **kwargs):
        try:
            raise KeystoneAdminRequired(method_name, self.admin_role)
        except:
            return fail(Failure())

    return f


class BaseKeystoneClient(object):
    admin_role = 'identity:admin'

    def __init__(self, keystone_url):
        self._client = HTTPClient.with_config()
        self._keystone_url = keystone_url.rstrip('/') + '/v2.0/'

    def _url(self, path):
        return self._keystone_url + '/'.join(path)

    def _request(self, method, path, *args, **kwargs):
        def _convert_errors(resp):
            if resp.length != 0:
                bd = json_content(resp)
            else:
                bd = succeed(None)

            if resp.code >= 400:
                bd.addCallback(
                    lambda body: Failure(KeystoneError(resp.code, body)))

            def _body_or_code(body):
                if body is None:
                    return resp.code

                return body

            bd.addCallback(_body_or_code)
            return bd

        if isinstance(path, list):
            uri = self._url(path)
        else:
            uri = path

        d = self._client.request(method, uri, *args, **kwargs)
        d.addCallback(_convert_errors)
        return d


class KeystoneClient(BaseKeystoneClient):
    def extensions(self):
        return self._request('get', ["extensions"])

    def authenticate(self, credentials):
        def _authenticated(resp):
            for role in resp['user']['roles']:
                if role['name'] == self.admin_role:
                    return _AdminKeystoneClient(
                        self._client, self._keystone_url, resp)

            return _AuthenticatedKeystoneClient(
                self._client, self._keystone_url, resp)

        d = self._request('post',
            ["tokens"],
            data=json.dumps({'auth': credentials}),
            headers={'content-type': ['application/json']}
        )
        d.addCallback(dict.get, 'access')
        d.addCallback(_authenticated)
        return d


class _AuthenticatedKeystoneClient(KeystoneClient):
    def __init__(self, client, keystone_url, auth_response):
        self.token_info = auth_response['token']
        self.service_catalog = auth_response['serviceCatalog']
        self.user_info = auth_response['user']

        self._keystone_url = keystone_url
        self._client = client

    def _request(self, method, path, *args, **kwargs):
        headers = kwargs.get('headers')
        if not headers:
            headers = {}

        if isinstance(headers, dict):
            headers = Headers(headers)

        headers.setRawHeaders('X-Auth-Token', [self.auth_token])

        kwargs['headers'] = headers

        return super(_AuthenticatedKeystoneClient, self)._request(
            method, path, *args, **kwargs)

    @property
    def tenant_id(self):
        return self.token_info['tenant']['id'].encode('utf-8')

    @property
    def auth_token(self):
        return self.token_info['id'].encode('utf-8')

    @property
    def user_id(self):
        return self.user_info['id'].encode('utf-8')

    def endpoints_for_service(self, name):
        for service in self.service_catalog:
            if service['name'] == name:
                return service['endpoints']

        return []

    def tenants(self):
        # XXX: Pagination?
        d = self._request('get', ['tenants'])
        d.addCallback(dict.get, 'tenants')
        return d

    validate_token = admin_required('validate_token')


def _code_to_bool(resp_code, accept_codes):
    return resp_code in accept_codes


class _AdminKeystoneClient(_AuthenticatedKeystoneClient):
    def validate_token(self, token):
        d = self._request('head', ['tokens', token])
        d.addCallback(_code_to_bool, (200, 203))
        return d

    def check_token(self, token, tenant_id):
        d = self._request('head', ['tokens', token],
                          params={'belongsTo': tenant_id})
        d.addCallback(_code_to_bool, (200, 203))
        return d

    def endpoints(self, token, tenant_id=None, limit=None):
        params = None
        if tenant_id is not None:
            params = {'belongsTo': tenant_id}

        d = self._request('get', ['tokens', token, 'endpoints'], params=params)
        d.addCallback(dict.get, 'endpoints')
        return d


if __name__ == '__main__':
    from txKeystone.client import KeystoneClient, KeystoneAdminRequired

    import sys
    from twisted.internet.task import react
    from twisted.internet.defer import inlineCallbacks

    @inlineCallbacks
    def main(reactor, *argv):
        kc = KeystoneClient('https://identity.api.rackspacecloud.com/')

        r = yield kc.extensions()
        print 1, r
        akc = yield kc.authenticate({'passwordCredentials': {'username': argv[0], 'password': argv[1]}})
        print 2, akc.user_info
        r = yield akc.endpoints_for_service('cloudServersOpenStack')
        print 3, r
        print akc.auth_token, akc.tenant_id, akc.user_id
        try:
            r = yield akc.validate_token(akc.auth_token)
            print 4, r
        except KeystoneAdminRequired as e:
            print 4, repr(e)

        r = yield akc.tenants()
        print 5, r

    react(main, sys.argv[1:])
