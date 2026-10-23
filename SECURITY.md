# Security Policy

## Supported Versions

| Version | Supported                                   |
| ------- | ------------------------------------------- |
| 5.x     | :white_check_mark: features and security    |
| 4.5.x   | :white_check_mark: security fixes only (`support/glancesv4`) |
| < 4.5   | :x:                                         |

## Reporting a Vulnerability

Please **do not open a public issue** for a security problem.

Report it privately through GitHub:
<https://github.com/nicolargo/glances/security/advisories/new>
(it reaches the maintainer only). Describe the issue, the affected version
or commit, the configuration needed, the steps to reproduce and the impact;
a proof of concept or a patch is welcome.

You get an acknowledgement within 7 days. The fix is released as a Glances
version and a GitHub Security Advisory (with a CVE when it applies), and you
are credited in the advisory and in `NEWS.rst` unless you prefer not to be.
Please keep the report private until then; once a fix is published, or the
report is declined, you are free to disclose it.

## Hardening a deployment

The REST API and the WebUI are served without authentication by default,
for a personal use on a private network. For anything else, read the
security section of the configuration documentation:
<https://glances.readthedocs.io/en/latest/config.html> (`[outputs]
password`, `webui_allowed_hosts`, `ssl_keyfile`, rate limiting).
