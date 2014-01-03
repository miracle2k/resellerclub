ResellerClub API in Python & Command Line Client
-------------------------------------------

This is a command line client for the `Resellerclub HTTP API`__. It can
also be used as a library (Python).

__ http://manage.resellerclub.com/kb/answer/744

For now, only a couple of DNS related functions are implemented. Pull
requests certainly welcome. Its straightforward to extend.


Usage:
------

DNS::

    $ resellerclub dns example.org add A foo 8.8.8.8
    $ resellerclub dns example.org delete A foo 8.8.8.8
    $ resellerclub dns example.org list A foo


Installation & Setup
-----------------

::
    $ pip install resellerclub

First, realize that Resellerclub requires you to whitelist your ip address
(they implement this whitelist on a firewall level). This is probably no good
if you want to use this tool on your workstation, so I encourage you setup
a proxy. You can find a ready-to-use docker image for such a proxy here:
https://index.docker.io/u/elsdoerfer/resellerclub-api-proxy/

You'll also need to determine your reseller id and your api key. The whole
thing is explained here:

    http://manage.resellerclub.com/kb/answer/753

You currently need to provide this data via environment variables. I suggest
you add them to your profile:

RESELLERCLUB_USER_ID
    Your reseller id

RESELLERCLUB_API_KEY
    Your API Key

RESELLERCLUB_URL
    Optional: The base url to use for the API. Unless you provide a
    proxy, this will be the default server that whitelists IPs.