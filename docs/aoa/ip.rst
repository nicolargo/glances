.. _ip:

IP
==

*Availability: all (private IP); public IP requires outbound network access*

Glances displays the private (LAN) IP address and, optionally, the public
(WAN) IP address queried from an online service.

Configuration (``[ip]`` section):

.. code-block:: ini

    [ip]
    disable=False
    refresh=60
    public_disabled=True
    public_refresh_interval=300
    public_api=https://ipv4.ipleak.net/json/
    public_field=ip
    public_template={continent_name}/{country_name}/{city_name}
    #public_username=<myname>
    #public_password=<mysecret>
    #public_api_allow_internal=false

- ``public_disabled`` — set to ``True`` on offline hosts (no public IP query).
- ``public_refresh_interval`` — seconds between public-IP refreshes (default 300).
- ``public_api`` — URL of a JSON service returning the public IP.
- ``public_field`` — JSON field holding the address (default ``ip``).
- ``public_template`` — human-readable summary built from the JSON fields.
- ``public_username`` / ``public_password`` — optional HTTP Basic Auth.

Hiding the public IP
--------------------

The ``--hide-public-info`` command-line flag masks the last two octets of
the public IP address in the interface (``a.b.c.d`` becomes ``a.b.*.*``).

SSRF hardening (``public_api_allow_internal``)
----------------------------------------------

``public_api`` is a fully operator-controlled URL, and
``public_username`` / ``public_password`` are attached to whatever host it
targets. To prevent Server-Side Request Forgery (CVE-2026-35587), Glances
enforces, on **every** refresh:

- **Scheme allowlist** — only ``http://`` and ``https://`` are accepted.
- **Internal-IP rejection (with DNS resolution)** — the URL host is
  resolved, and if **any** resolved address is loopback, link-local
  (including the cloud-metadata address ``169.254.169.254``), private
  (RFC1918) or reserved, the request is **skipped** — so credentials are
  never sent to an internal host. Resolving on each refresh also defeats
  DNS-alias / rebinding tricks that point a public hostname at an internal
  address.

This protection is **on by default** and safe for the common case (public
services such as ipleak). If you deliberately run your own public-IP
service on a private or loopback address, opt out with:

.. code-block:: ini

    [ip]
    public_api_allow_internal=true

You can disable the whole plugin with ``--disable-plugin ip`` or the ``I``
key in the interface.
