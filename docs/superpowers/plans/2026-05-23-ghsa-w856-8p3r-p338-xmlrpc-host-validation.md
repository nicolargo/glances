# GHSA-w856-8p3r-p338 — XML-RPC Host Validation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in HTTP `Host` header validation to the Glances XML-RPC server (`glances -s`) via a new `xmlrpc_allowed_hosts` config key to mitigate DNS rebinding (CVE-2026-46611), without changing default behaviour.

**Architecture:** Override `GlancesXMLRPCHandler.parse_request()` to consult an allowlist read from `[outputs] xmlrpc_allowed_hosts` and stored on the server instance. Reject mismatching `Host` headers with HTTP 400 *before* authentication. Add a startup warning when the allowlist is empty (mirrors the existing REST/WebUI warning). Wildcards supported via `fnmatch`.

**Tech Stack:** Python stdlib (`xmlrpc.server`, `fnmatch`, `http.server`), `defusedxml`, pytest, `requests`. Spec: `docs/superpowers/specs/2026-05-23-ghsa-w856-8p3r-p338-xmlrpc-host-validation-design.md`.

---

## File Structure

- **Modify** `glances/server.py` — `GlancesXMLRPCHandler.parse_request`, `GlancesXMLRPCServer.__init__`, `GlancesServer.__init__`
- **Modify** `conf/glances.conf` — add commented `xmlrpc_allowed_hosts` entry in `[outputs]`
- **Modify** `docs/quickstart.rst` — append security section under *Client/Server Mode*
- **Create** `tests/test_xmlrpc_server.py` — new pytest module covering the six acceptance scenarios from the spec

Each task below produces a self-contained, committable change. The plan uses strict TDD: write failing test → minimal implementation → green → commit.

---

## Task 1 — Bootstrap the XML-RPC test module

**Files:**
- Create: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Create the test scaffold with the server-launch fixture**

Mirror the `subprocess.Popen` pattern from `tests/test_restful.py` (test_000 / test_999). The server reads `./conf/glances.conf` (which won't yet contain `xmlrpc_allowed_hosts`, so default = permissive). Use a high free port to avoid collisions with a running glances.

```python
#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances XML-RPC server Host header validation
(GHSA-w856-8p3r-p338 / CVE-2026-46611)."""

import shlex
import subprocess
import sys
import time
import unittest

import requests

SERVER_PORT = 62209  # high port, separate from REST tests
URL = f"http://127.0.0.1:{SERVER_PORT}/RPC2"

XMLRPC_BODY = (
    '<?xml version="1.0"?>'
    '<methodCall><methodName>init</methodName></methodCall>'
)


pid = None


class TestGlancesXmlrpc(unittest.TestCase):
    """Glances XML-RPC server Host header validation tests."""

    def setUp(self):
        print('\n' + '=' * 78)

    def post(self, host_header):
        """POST an XML-RPC call with a specific Host header."""
        return requests.post(
            URL,
            data=XMLRPC_BODY,
            headers={'Host': host_header, 'Content-Type': 'text/plain'},
            timeout=5,
        )

    def test_000_start_server(self):
        """Start the Glances XML-RPC server (no allowlist configured)."""
        global pid
        print('INFO: [TEST_000] Start the Glances XML-RPC Server')
        cmdline = sys.executable
        cmdline += (
            f" -m glances -B 127.0.0.1 -s -p {SERVER_PORT}"
            " --disable-autodiscover -C ./conf/glances.conf"
        )
        print(f"Run: {cmdline}")
        pid = subprocess.Popen(shlex.split(cmdline))
        print("Wait 5 seconds for server start...")
        time.sleep(5)
        self.assertIsNotNone(pid)

    def test_999_stop_server(self):
        """Stop the Glances XML-RPC server."""
        print('INFO: [TEST_999] Stop server')
        pid.terminate()
        time.sleep(1)
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the bootstrap to verify start/stop works against the current (unpatched) server**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 2 tests pass (`test_000_start_server`, `test_999_stop_server`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): scaffold for Host header validation tests"
```

---

## Task 2 — Regression test: default behaviour is permissive

This locks in the *current* behaviour before we change anything. With no `xmlrpc_allowed_hosts` configured, any `Host` header is accepted.

**Files:**
- Modify: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Add the permissive-default test**

Insert between `test_000_start_server` and `test_999_stop_server`:

```python
    def test_001_default_accepts_any_host(self):
        """Without xmlrpc_allowed_hosts set, any Host header is accepted."""
        print('INFO: [TEST_001] Default = permissive (no allowlist)')
        r = self.post('attacker.example.com')
        self.assertEqual(r.status_code, 200)
        self.assertIn('<methodResponse>', r.text)
```

- [ ] **Step 2: Run the test against the current (unpatched) server**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 3 tests pass. `test_001` proves the vulnerability exists on master/develop today — this is the *regression baseline*.

- [ ] **Step 3: Commit**

```bash
git add tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): lock in current permissive default (regression baseline)"
```

---

## Task 3 — Failing test: allowlist rejects spoofed Host

We now add a *second* config file used only for this and later tests, with `xmlrpc_allowed_hosts` set. The test launches a second server instance on a different port using that config.

**Files:**
- Create: `tests/conf/glances_xmlrpc_allowed_hosts.conf`
- Modify: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Create a minimal test config file**

Create `tests/conf/glances_xmlrpc_allowed_hosts.conf`:

```ini
[outputs]
xmlrpc_allowed_hosts=127.0.0.1,*.glances.test
```

- [ ] **Step 2: Add a second server fixture and the reject test**

Add `SECURE_PORT` constant, `SECURE_URL`, a second `pid_secure` global, and the test:

```python
SECURE_PORT = 62210
SECURE_URL = f"http://127.0.0.1:{SECURE_PORT}/RPC2"

pid_secure = None


# Inside TestGlancesXmlrpc:

    def post_secure(self, host_header):
        return requests.post(
            SECURE_URL,
            data=XMLRPC_BODY,
            headers={'Host': host_header, 'Content-Type': 'text/plain'},
            timeout=5,
        )

    def test_010_start_secure_server(self):
        """Start a second server with xmlrpc_allowed_hosts configured."""
        global pid_secure
        print('INFO: [TEST_010] Start secured XML-RPC server')
        cmdline = sys.executable
        cmdline += (
            f" -m glances -B 127.0.0.1 -s -p {SECURE_PORT}"
            " --disable-autodiscover"
            " -C ./tests/conf/glances_xmlrpc_allowed_hosts.conf"
        )
        pid_secure = subprocess.Popen(shlex.split(cmdline))
        time.sleep(5)
        self.assertIsNotNone(pid_secure)

    def test_011_secure_rejects_spoofed_host(self):
        """xmlrpc_allowed_hosts=127.0.0.1 → reject Host: attacker."""
        print('INFO: [TEST_011] Spoofed Host rejected with 400')
        r = self.post_secure('attacker.example.com')
        self.assertEqual(r.status_code, 400)
```

And add to `test_999_stop_server` so the second server is killed too:

```python
    def test_999_stop_server(self):
        print('INFO: [TEST_999] Stop both servers')
        pid.terminate()
        if pid_secure is not None:
            pid_secure.terminate()
        time.sleep(1)
        self.assertTrue(True)
```

- [ ] **Step 3: Run the tests to verify the new ones fail**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: `test_010_start_secure_server` PASSES (server starts and ignores the unknown config key today). `test_011_secure_rejects_spoofed_host` FAILS with `200 != 400` because the current server has no Host validation.

This failure is the green light to implement the feature.

- [ ] **Step 4: Commit the failing test**

```bash
git add tests/conf/glances_xmlrpc_allowed_hosts.conf tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): failing test — spoofed Host should be rejected (CVE-2026-46611)"
```

---

## Task 4 — Implement Host validation in `GlancesXMLRPCHandler`

**Files:**
- Modify: `glances/server.py`

- [ ] **Step 1: Add `fnmatch` import**

In `glances/server.py`, just below the existing `import socket` line:

```python
import fnmatch
```

- [ ] **Step 2: Read `xmlrpc_allowed_hosts` in `GlancesXMLRPCServer.__init__`**

In `glances/server.py`, inside `GlancesXMLRPCServer.__init__`, add **immediately after** the existing `cors_origins` block (before `try: self.address_family = ...`):

```python
        # DNS rebinding protection (GHSA-w856-8p3r-p338 / CVE-2026-46611).
        # When xmlrpc_allowed_hosts is set, the handler rejects requests whose
        # Host header does not match any of the listed patterns. Default is
        # None (permissive) for backward compatibility — a startup warning is
        # emitted by GlancesServer when the allowlist is empty.
        if config is not None:
            self.allowed_hosts = config.get_list_value(
                'outputs', 'xmlrpc_allowed_hosts', default=None
            )
        else:
            self.allowed_hosts = None
```

- [ ] **Step 3: Update `GlancesXMLRPCHandler.parse_request` to validate Host before auth**

Replace the existing `parse_request` method:

```python
    def parse_request(self):
        if not xmlrpc.xmlrpc_server.SimpleXMLRPCRequestHandler.parse_request(self):
            return False
        # Host header validation (DNS rebinding protection).
        # Runs before authentication so that a spoofed Host is rejected
        # regardless of credentials — this avoids leaking valid host names
        # via auth-error differentials.
        allowed_hosts = getattr(self.server, 'allowed_hosts', None)
        if allowed_hosts:
            host = self.headers.get('Host', '').split(':')[0]
            if not any(fnmatch.fnmatchcase(host, pat) for pat in allowed_hosts):
                self.send_error(400, 'Bad Request: invalid Host header')
                return False
        if self.authenticate(self.headers):
            return True
        self.send_error(401, 'Authentication failed')
        return False
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: all 4 tests pass — `test_011_secure_rejects_spoofed_host` is now green; `test_001_default_accepts_any_host` still green (no regression).

- [ ] **Step 5: Commit**

```bash
git add glances/server.py
git commit -m "fix(server): validate Host header in XML-RPC server (GHSA-w856-8p3r-p338)

Add opt-in DNS rebinding protection to the XML-RPC server via a new
xmlrpc_allowed_hosts config key in [outputs]. When set, the handler
rejects requests whose Host header does not match any of the listed
patterns (fnmatch wildcards supported). Default is permissive for
backward compatibility.

Mitigates CVE-2026-46611."
```

---

## Task 5 — Test: allowlisted Host is accepted

**Files:**
- Modify: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Add the positive-match test**

Insert after `test_011`:

```python
    def test_012_secure_accepts_listed_host(self):
        """Allowlisted Host returns 200."""
        print('INFO: [TEST_012] Allowlisted Host accepted')
        r = self.post_secure('127.0.0.1')
        self.assertEqual(r.status_code, 200)
        self.assertIn('<methodResponse>', r.text)
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): allowlisted Host returns 200"
```

---

## Task 6 — Test: wildcard match

**Files:**
- Modify: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Add wildcard tests**

The test config file already includes `*.glances.test`. Add both a positive and a negative case:

```python
    def test_013_secure_wildcard_match(self):
        """Wildcard pattern *.glances.test matches subdomain."""
        print('INFO: [TEST_013] Wildcard match')
        r = self.post_secure('node1.glances.test')
        self.assertEqual(r.status_code, 200)

    def test_014_secure_wildcard_no_bare_match(self):
        """*.glances.test does NOT match the bare domain glances.test."""
        print('INFO: [TEST_014] Wildcard does not match bare domain')
        r = self.post_secure('glances.test')
        self.assertEqual(r.status_code, 400)
```

- [ ] **Step 2: Run the tests**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 7 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): wildcard Host patterns via fnmatch"
```

---

## Task 7 — Test: port stripping and missing Host header

**Files:**
- Modify: `tests/test_xmlrpc_server.py`

- [ ] **Step 1: Add port-stripping test**

```python
    def test_015_secure_strips_port(self):
        """Host: 127.0.0.1:62210 matches the bare 127.0.0.1 entry."""
        print('INFO: [TEST_015] Port is stripped before matching')
        r = self.post_secure(f'127.0.0.1:{SECURE_PORT}')
        self.assertEqual(r.status_code, 200)
```

- [ ] **Step 2: Add missing-Host test**

The `requests` library always sets a Host header. To test the absent-header path, use a low-level socket. Add the test:

```python
    def test_016_secure_missing_host_rejected(self):
        """HTTP/1.0 request with no Host header → 400."""
        import socket
        print('INFO: [TEST_016] Missing Host header rejected')
        s = socket.create_connection(('127.0.0.1', SECURE_PORT), timeout=5)
        body = XMLRPC_BODY.encode()
        req = (
            b'POST /RPC2 HTTP/1.0\r\n'
            b'Content-Type: text/plain\r\n'
            b'Content-Length: ' + str(len(body)).encode() + b'\r\n'
            b'\r\n' + body
        )
        s.sendall(req)
        resp = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        s.close()
        self.assertIn(b'400', resp.split(b'\r\n', 1)[0])
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 9 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_xmlrpc_server.py
git commit -m "test(xmlrpc): port stripping and missing-Host edge cases"
```

---

## Task 8 — Startup warning when allowlist is empty

**Files:**
- Modify: `glances/server.py`

- [ ] **Step 1: Add the warning in `GlancesServer.__init__`**

In `glances/server.py`, just after the existing CORS warning block (which currently ends with the `logger.warning("XML-RPC server is running without authentication...")` call), insert:

```python
        # DNS rebinding protection warning
        if not getattr(self.server, 'allowed_hosts', None):
            print(
                "WARNING: Glances XML-RPC server is running without Host header validation.\n"
                "         DNS rebinding attacks may allow untrusted pages to read the XML-RPC API.\n"
                "         Set xmlrpc_allowed_hosts in glances.conf [outputs] to restrict access:\n"
                "           xmlrpc_allowed_hosts=localhost,127.0.0.1,<your-hostname>"
            )
            logger.warning(
                "XML-RPC server is running without Host header validation (DNS rebinding protection)"
            )
```

- [ ] **Step 2: Run the full test suite to verify no regression**

Run: `pytest tests/test_xmlrpc_server.py -v`
Expected: 9 tests still pass. The warning is emitted to stdout — pytest captures it but does not fail on it.

- [ ] **Step 3: Manual smoke check**

Run: `python -m glances -s -p 62299 --disable-autodiscover -C ./conf/glances.conf &`
Expected stdout includes:
```
WARNING: Glances XML-RPC server is running without Host header validation.
         DNS rebinding attacks may allow untrusted pages to read the XML-RPC API.
         Set xmlrpc_allowed_hosts in glances.conf [outputs] to restrict access:
           xmlrpc_allowed_hosts=localhost,127.0.0.1,<your-hostname>
```
Kill the process: `pkill -f "glances -s -p 62299"`.

- [ ] **Step 4: Commit**

```bash
git add glances/server.py
git commit -m "feat(server): warn at startup when XML-RPC server has no Host allowlist"
```

---

## Task 9 — Add the config key to `conf/glances.conf`

**Files:**
- Modify: `conf/glances.conf`

- [ ] **Step 1: Insert the commented block under the existing MCP block**

In `conf/glances.conf`, after the existing `#mcp_allowed_hosts=...` line (around line 96), insert:

```ini
#
# DNS rebinding protection for the XML-RPC server (glances -s)
# Restrict the HTTP Host header accepted by the XML-RPC server.
# Comma-separated list of hostnames or IPs. Wildcards supported (e.g. *.example.com).
# When this key is absent or commented out, no host filtering is applied (default behaviour).
# Recommended for any internet-facing or multi-tenant deployment.
#xmlrpc_allowed_hosts=localhost,127.0.0.1,myserver.example.com
```

- [ ] **Step 2: Commit**

```bash
git add conf/glances.conf
git commit -m "docs(conf): document xmlrpc_allowed_hosts in glances.conf"
```

---

## Task 10 — Document the new setting in `docs/quickstart.rst`

**Files:**
- Modify: `docs/quickstart.rst`

- [ ] **Step 1: Append a security section after the current Client/Server Mode block**

In `docs/quickstart.rst`, immediately after the existing `In client/server mode, limits are set by the server side.` line (around line 90), insert:

```rst

Security — DNS rebinding protection (XML-RPC)
'''''''''''''''''''''''''''''''''''''''''''''

By default the XML-RPC server accepts requests with any value of the HTTP
``Host`` header. A malicious web page can exploit DNS rebinding to read the
server's response from a victim's browser
(`CVE-2026-46611 <https://github.com/nicolargo/glances/security/advisories/GHSA-w856-8p3r-p338>`_).

**Enable Host validation** by setting ``xmlrpc_allowed_hosts`` in the
``[outputs]`` section of ``glances.conf``:

.. code-block:: ini

    [outputs]
    xmlrpc_allowed_hosts=localhost,127.0.0.1,myserver.example.com

When set, requests whose ``Host`` header does not match any of the listed
patterns are rejected with ``400 Bad Request``. Wildcards follow Python
``fnmatch`` rules — for example ``*.example.com`` matches ``foo.example.com``
but not ``example.com`` itself.

For any deployment on a non-loopback interface, always set
``xmlrpc_allowed_hosts``. A startup warning is emitted when it is absent.
```

- [ ] **Step 2: Build the docs locally to verify rendering (optional but recommended)**

Run: `cd docs && make html 2>&1 | tail -20`
Expected: no Sphinx warnings related to the new section.

- [ ] **Step 3: Commit**

```bash
git add docs/quickstart.rst
git commit -m "docs(quickstart): document xmlrpc_allowed_hosts DNS rebinding protection"
```

---

## Task 11 — Lint, format, full-suite check

**Files:** none modified — verification only.

- [ ] **Step 1: Run lint and format**

Run: `make lint && make format`
Expected: both pass with no errors. If `make format` produces diffs, commit them as a follow-up:

```bash
git add -p
git commit -m "style: apply make format"
```

- [ ] **Step 2: Run the full test suite (sanity check)**

Run: `pytest tests/test_xmlrpc_server.py tests/test_restful.py -v`
Expected: all tests pass.

- [ ] **Step 3: Manual end-to-end PoC**

Reproduce the advisory's PoC against a server *with* the allowlist:

```bash
python -m glances -s -p 62299 --disable-autodiscover \
    -C ./tests/conf/glances_xmlrpc_allowed_hosts.conf &
sleep 3
curl -s -o /dev/null -w "spoofed=%{http_code}\n" \
    -X POST http://127.0.0.1:62299/RPC2 \
    -H "Host: attacker.example.com" \
    -H "Content-Type: text/plain" \
    -d '<?xml version="1.0"?><methodCall><methodName>init</methodName></methodCall>'
curl -s -o /dev/null -w "legit=%{http_code}\n" \
    -X POST http://127.0.0.1:62299/RPC2 \
    -H "Host: 127.0.0.1" \
    -H "Content-Type: text/plain" \
    -d '<?xml version="1.0"?><methodCall><methodName>init</methodName></methodCall>'
pkill -f "glances -s -p 62299"
```

Expected output:
```
spoofed=400
legit=200
```

- [ ] **Step 4: Stop. Do not push, do not open the PR.**

Per project policy (see global CLAUDE.md memory `feedback_never_push_or_open_pr`), the maintainer handles `git push` and `gh pr create` themselves. Final hand-back message:

```
Patch ready on branch GHSA-w856-8p3r-p338. All tests green, lint clean,
manual PoC confirms spoofed=400 / legit=200. Ready for your push.
```

---

## Acceptance summary (matches spec §Acceptance criteria)

1. ✅ No-config behaviour identical to today — `test_001_default_accepts_any_host` (Task 2).
2. ✅ PoC `Host: attacker.example.com` returns 400 with allowlist set — Task 11 step 3.
3. ✅ New tests pass (Tasks 1–7), existing tests still pass — Task 11 step 2.
4. ✅ `make lint && make format` clean — Task 11 step 1.
5. ✅ Doc section renders — Task 10 step 2.
