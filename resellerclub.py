import sys, os
import textwrap
try:
    from urllib.parse import urljoin
except ImportError:
    # Python 2.7
    from urlparse import urljoin
import json
from collections import namedtuple
from functools import wraps
from docopt import docopt
import requests


DEFAULT_URL = 'https://httpapi.com/api/'
#DEAFULT_URL = 'https://test.httpapi.com/'

MAX_RECORDS = 50  # 50 is the current max

class Address(namedtuple('Address', 'line_1 line_2 line_3 city state country zipcode')):
    def to_params(self):
        return {
            'address-line-1': self.line_1,
            'self-line-2': self.line_2,
            'self-line-3': self.line_3,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'zipcode': self.zipcode
        }

class ResellerError(RuntimeError):
    pass

def check_error(res):
    if isinstance(res, dict):
        status = res.get('status')
        if status and status == 'ERROR':
            raise ResellerError(res['message'])
    return res

def append_slash(url):
    if not url.endswith('/'):
        return url + '/'
    return url

class ApiClient(object):

    def __init__(self, user_id, api_key, url=None, proxies=None):
        self.url = url or DEFAULT_URL
        self.session = requests.session()
        self.proxies = proxies
        self.session.params = {
            'auth-userid': user_id,
            'api-key': api_key
        }

    def request(self, http_method, api_method, params):
        path = '{}.json'.format(api_method)
        response = self.session.request(
            http_method, urljoin(append_slash(self.url), path), params=params, proxies=self.proxies)
        return response.json()

    def domains_get_details(self, name):
        return self.request('GET', 'domains/details-by-name', {
            'domain-name': name,
            'options': 'All'
        })

    def domains_register(self, domain, years, ns, customer, reg_contact,
        admin_contact, tech_contact, billing_contact, invoice_option, purchase_privacy,
        protect_privacy):
        """
        :param str domain: domain name to register
        :param int years: number of years to register for
        :param list[str] ns: list of nameservers
        :param int customer: customer to register on behalf of
        :param int reg_contact:
        :param int admin_contact:
        :param int tech_contact:
        :param int billing_contact:
        :param str invoice_option: one of NoInvoice, PayInvoice, or KeepInvoice
        :param bool purchase_privacy: optional
        :param bool protect_privacy: optional
        """
        return check_error(self.request('POST', 'domains/register', {
            'domain-name': domain,
            'years': years,
            'ns': ns,
            'customer-id': customer,
            'reg-contact-id': reg_contact,
            'admin-contact-id': admin_contact,
            'tech-contact-id': tech_contact,
            'billing-contact-id': billing_contact,
            'invoice-option': invoice_option,
            'purchase-privacy': purchase_privacy,
            'protect-privacy': protect_privacy
        }))

    def domains_default_ns(self, customer_id):
        """Return default name servers for a customer

        :param customer_id:
        """
        return check_error(self.request('GET', 'domains/customer-default-ns', {
            'customer-id': customer_id
        }))

    def contacts_add(self, type, name, company, email, address, phone_cc, phone, customer_id):
        """
        :param type:
        :param name: name of the contact
        :param company: name of company
        :param email:
        :param address:
        :param phone_cc:
        :param phone:
        :param customer_id:
        """
        params = {
            'type': type,
            'name': name,
            'company': company,
            'email': email,
            'phone-cc': phone_cc,
            'phone': phone,
            'customer-id': customer_id
        }
        params.update(address.to_params())
        return check_error(self.request('POST', 'contacts/add', params))

    def customers_add(self, username, password, name, company, address, phone_cc,
        phone, lang_pref):
        """
        :param username: email address
        :param password:
        :param name:
        :param company:
        :param address:
        :param phone_cc:
        :param phone:
        :param lang_pref:
        """
        params = {
            'username': username,
            'passwd': password,
            'name': name,
            'company': company,
            'phone-cc': phone_cc,
            'phone': phone,
            'lang-pref': lang_pref
        }
        params.update(address.to_params())
        return check_error(self.request('POST', 'customers/signup', params))


    def domains_check_availability(self, domain, tlds, suggest_alternative=False):
        """
        :param domain: domain to check availability for
        :param tlds: tlds of the domains to check
        :param suggest_alternative: True to return a list of alternative domain names
        """
        return check_error(self.request('GET', 'domains/available', {
            'domain-name': domain,
            'tlds': tlds,
            'suggest-alternative': suggest_alternative
        }))

    def dns_activate(self, domain_name):
        order_id = self.domains_get_details(domain_name)['entityid']
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
           {prog} dns <domain> activate

    Currently supported record types:
        A, AAAA, CNAME

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

    if args['activate']:
        result = cmd_activate(client, args)
    else:
        result = cmd_domain(client, args)

    if result is None:
        return

    print(json.dumps(result, sort_keys=True, indent=2))
    if 'error' in result:
        return 1


def cmd_activate(client, args):
    return client.dns_activate(args['<domain>'])


def cmd_domain(client, args):
    try:
        part_for_record = {
            'A': 'ipv4',
            'AAAA': 'ipv6',
            'CNAME': 'cname',
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
    return result

def run():
    sys.exit(main(sys.argv) or 0)


if __name__ == '__main__':
    run()
