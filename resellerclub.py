import sys, os
import textwrap
from urllib.parse import urljoin
import json
from functools import wraps
from docopt import docopt
import requests


DEFAULT_URL = 'https://httpapi.com/'
#DEAFULT_URL = 'https://test.httpapi.com/'

MAX_RECORDS = 50  # 50 is the current max

class ApiClient(object):

    def __init__(self, user_id, api_key, url=None):
        self.url = url or DEFAULT_URL
        self.session = requests.Session()
        self.session.params = {
            'auth-userid': user_id,
            'api-key': api_key
        }

    def request(self, http_method, api_method, params):
        path = '/api/{}.json'.format(api_method)
        return self.session.request(
            http_method, urljoin(self.url, path), params=params).json()

    def dns_activate(self, order_id):
        return self.request('POST', 'dns/activate', {
            'order-id': order_id,
        })

    def dns_search(self, domain, type, no_of_records=10, host=None):
        return self.request('GET', 'dns/manage/search-records', {
            'domain-name': domain,
            'type': type,
            'no-of-records': no_of_records,
            'page-no': 1,
            'host': host
        })

    def dns_add_record(self, record_type, domain, value, host=None, ttl=None):
        return self.request('POST', 'dns/manage/add-{}-record'.format(record_type), {
            'domain-name': domain,
            'value': value,
            'host': host,
            'ttl': ttl or None
        })

    def dns_delete_record(self, record_type, domain, value, host=None):
        return self.request('POST', 'dns/manage/delete-{}-record'.format(record_type), {
            'domain-name': domain,
            'value': value,
            'host': host,
        })

# The DNS record functions for the different types are all separate, but
# with essentially the same signature. Do not duplicate all that code.
for record_type in ('ipv4', 'ipv6', 'cname'):
    # 3.4 will have functools.partialmethod
    def make_funcs(record_type):
        @wraps(ApiClient.dns_add_record)
        def add(self, *a, **kw):
            return ApiClient.dns_add_record(self, record_type, *a, **kw)
        @wraps(ApiClient.dns_delete_record)
        def delete(self, *a, **kw):
            return ApiClient.dns_delete_record(self, record_type, *a, **kw)
        return add, delete
    add, delete = make_funcs(record_type)
    setattr(ApiClient, 'dns_add_{}_record'.format(record_type), add)
    setattr(ApiClient, 'dns_delete_{}_record'.format(record_type), delete)


def main(argv):
    """
    usage: {prog} dns <domain> add <record-type> <name> <value> [--ttl int]
           {prog} dns <domain> delete <record-type> <name> <value>
           {prog} dns <domain> list <record-type> <name>

    Currently supported record types:
        A, AAAA

    Commands:
        add          will add an ip for the given name
        remote    will remove an ip for the given name
        list            will show all ips for the given name

    Examples:
        $ {prog} dns example.org add A foo 8.8.8.8
        $ {prog} dns example.org delete A foo 8.8.8.8
    """
    args = docopt(
        textwrap.dedent(main.__doc__.format(prog=argv[0])),
        argv[1:])

    client = ApiClient(
        os.environ['RESELLERCLUB_USER_ID'],
        os.environ['RESELLERCLUB_API_KEY'],
        url=os.environ.get('RESELLERCLUB_URL'))

    try:
        part_for_record = {
            'A': 'ipv4',
            'AAAA': 'ipv6',
        }[args['<record-type>']]
    except KeyError:
        print('Not a supported record type: {}'.format(args['<record-type>']))
        return

    if args['add']:
        method = 'dns_add_{}_record'.format(part_for_record)
        result = getattr(client, method)(args['<domain>'], args['<value>'],
            host=args['<name>'], ttl=args['--ttl'])
    elif args['delete']:
        method = 'dns_delete_{}_record'.format(part_for_record)
        result = getattr(client, method)(args['<domain>'], args['<value>'], host=args['<name>'])
    elif args['list']:
        result = client.dns_search(args['<domain>'], args['<record-type>'], host=args['<name>'], no_of_records=MAX_RECORDS)

    print(json.dumps(result, sort_keys=True, indent=2))
    if 'error' in result:
        return 1


def run():
    sys.exit(main(sys.argv) or 0)


if __name__ == '__main__':
    run()