Example Usage:

```Python
from twisted.internet import reactor
from twisted.web.client import Agent

from txKeystone import KeystoneAgent

agent = Agent(reactor)

RACKSPACE_USERNAME = '' # your username here
RACKSPACE_APIKEY = '' # your API key here
AUTH_URL = 'https://identity.api.rackspacecloud.com/v2.0/tokens'

keystone_agent = KeystoneAgent(agent,
                               AUTH_URL,
                               (RACKSPACE_USERNAME, RACKSPACE_APIKEY))

```

```keystone_agent``` can now be used like a [twisted.web.client.Agent](http://twistedmatrix.com/documents/10.1.0/web/howto/client.html) (see "Receiving Responses") to make requests to Rackspace APIs, and the X-Tenant-Id and X-Auth-Token headers will be set automatically.
