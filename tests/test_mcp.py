#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the MCP server."""

import asyncio
import base64
import os
import shlex
import subprocess
import time
import unittest

import requests
from pydantic import AnyUrl

from glances import __version__
from glances.outputs.glances_restful_api import GlancesMcpAuthMiddleware

try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

SERVER_PORT = 61235  # Different port from test_restful.py to allow parallel runs
MCP_BASE_URL = f"http://localhost:{SERVER_PORT}/mcp"
MCP_SSE_URL = f"{MCP_BASE_URL}/sse"

pid = None

print(f'MCP server unitary tests for Glances {__version__}')


def run_async(coro):
    """Run an async coroutine in tests (works with any Python ≥ 3.10)."""
    return asyncio.run(coro)


@unittest.skipUnless(MCP_AVAILABLE, "mcp package is not installed")
class TestGlancesMcp(unittest.TestCase):
    """Test the Glances MCP server."""

    def setUp(self):
        print('\n' + '=' * 78)

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def test_000_start_server(self):
        """Start the Glances web server with --enable-mcp."""
        global pid

        print('INFO: [TEST_000] Start the Glances Web Server with MCP enabled')
        if os.path.isfile('.venv/bin/python'):
            cmdline = ".venv/bin/python"
        else:
            cmdline = "python"
        cmdline += (
            f" -m glances -B 0.0.0.0 -w --disable-webui"
            f" -p {SERVER_PORT} --disable-autodiscover"
            f" --enable-mcp -C ./conf/glances.conf"
        )
        print(f"Run the Glances Web Server with MCP on port {SERVER_PORT}")
        pid = subprocess.Popen(shlex.split(cmdline))
        print("Please wait 5 seconds...")
        time.sleep(5)

        self.assertIsNotNone(pid)

    # ------------------------------------------------------------------
    # HTTP-level smoke tests (no MCP client needed)
    # ------------------------------------------------------------------

    def test_001_sse_endpoint_reachable(self):
        """SSE endpoint must answer with Content-Type: text/event-stream."""
        print(f'INFO: [TEST_001] Check SSE endpoint at {MCP_SSE_URL}')
        # stream=True so requests does not wait for the body (SSE keeps open)
        resp = requests.get(MCP_SSE_URL, stream=True, timeout=5)
        self.assertEqual(resp.status_code, 200)
        content_type = resp.headers.get('content-type', '')
        self.assertIn('text/event-stream', content_type, f"Expected text/event-stream, got {content_type}")
        resp.close()

    # ------------------------------------------------------------------
    # MCP client tests — resources
    # ------------------------------------------------------------------

    def test_010_list_resources(self):
        """MCP client must receive the expected static resources."""
        print('INFO: [TEST_010] List MCP resources via client')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_resources()
                    return [str(r.uri) for r in result.resources]

        uris = run_async(_run())
        print(f"Resources returned: {uris}")
        self.assertIn('glances://plugins', uris)
        self.assertIn('glances://stats', uris)
        self.assertIn('glances://limits', uris)

    def test_011_list_resource_templates(self):
        """MCP client must receive the expected resource templates."""
        print('INFO: [TEST_011] List MCP resource templates via client')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_resource_templates()
                    return [t.uriTemplate for t in result.resourceTemplates]

        templates = run_async(_run())
        print(f"Resource templates returned: {templates}")
        self.assertIn('glances://stats/{plugin}', templates)
        self.assertIn('glances://stats/{plugin}/history', templates)
        self.assertIn('glances://limits/{plugin}', templates)

    def test_012_read_resource_plugins(self):
        """glances://plugins must return a non-empty JSON list."""
        print('INFO: [TEST_012] Read glances://plugins resource')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.read_resource(AnyUrl('glances://plugins'))
                    return result.contents

        contents = run_async(_run())
        self.assertTrue(len(contents) > 0)
        import json

        plugins = json.loads(contents[0].text)
        print(f"Plugins list: {plugins[:5]}...")
        self.assertIsInstance(plugins, list)
        self.assertIn('cpu', plugins)
        self.assertIn('mem', plugins)

    def test_013_read_resource_all_stats(self):
        """glances://stats must return a dict keyed by plugin name."""
        print('INFO: [TEST_013] Read glances://stats resource')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.read_resource(AnyUrl('glances://stats'))
                    return result.contents

        contents = run_async(_run())
        import json

        stats = json.loads(contents[0].text)
        print(f"All stats keys: {list(stats.keys())[:5]}...")
        self.assertIsInstance(stats, dict)
        self.assertIn('cpu', stats)
        self.assertIn('mem', stats)

    def test_014_read_resource_plugin_cpu(self):
        """glances://stats/cpu must return a dict with expected CPU fields."""
        print('INFO: [TEST_014] Read glances://stats/cpu resource template')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.read_resource(AnyUrl('glances://stats/cpu'))
                    return result.contents

        contents = run_async(_run())
        import json

        cpu = json.loads(contents[0].text)
        print(f"CPU stats keys: {list(cpu.keys())}")
        self.assertIsInstance(cpu, dict)
        self.assertIn('total', cpu)

    def test_015_read_resource_limits_cpu(self):
        """glances://limits/cpu must return a dict with threshold keys."""
        print('INFO: [TEST_015] Read glances://limits/cpu resource template')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.read_resource(AnyUrl('glances://limits/cpu'))
                    return result.contents

        contents = run_async(_run())
        import json

        limits = json.loads(contents[0].text)
        print(f"CPU limits: {limits}")
        self.assertIsInstance(limits, dict)

    # ------------------------------------------------------------------
    # MCP client tests — prompts
    # ------------------------------------------------------------------

    def test_020_list_prompts(self):
        """MCP client must receive the four expected prompt templates."""
        print('INFO: [TEST_020] List MCP prompts via client')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_prompts()
                    return [p.name for p in result.prompts]

        names = run_async(_run())
        print(f"Prompts returned: {names}")
        self.assertIn('system_health_summary', names)
        self.assertIn('alert_analysis', names)
        self.assertIn('top_processes_report', names)
        self.assertIn('storage_health', names)

    def test_021_get_prompt_system_health(self):
        """system_health_summary prompt must return a non-empty text message."""
        print('INFO: [TEST_021] Get system_health_summary prompt')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.get_prompt('system_health_summary')
                    return result.messages

        messages = run_async(_run())
        self.assertTrue(len(messages) > 0)
        text = messages[0].content.text
        print(f"Prompt text (first 120 chars): {text[:120]}")
        self.assertIn('Glances', text)
        self.assertIn('cpu', text.lower())

    def test_022_get_prompt_alert_analysis_with_arg(self):
        """alert_analysis prompt must accept the 'level' argument."""
        print('INFO: [TEST_022] Get alert_analysis prompt with level=critical')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.get_prompt('alert_analysis', arguments={'level': 'critical'})
                    return result.messages

        messages = run_async(_run())
        self.assertTrue(len(messages) > 0)
        text = messages[0].content.text
        self.assertIn('critical', text)

    def test_023_get_prompt_top_processes_with_arg(self):
        """top_processes_report prompt must accept the 'nb' argument."""
        print('INFO: [TEST_023] Get top_processes_report prompt with nb=5')

        async def _run():
            async with sse_client(MCP_SSE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.get_prompt('top_processes_report', arguments={'nb': '5'})
                    return result.messages

        messages = run_async(_run())
        self.assertTrue(len(messages) > 0)
        text = messages[0].content.text
        self.assertIn('5', text)

    # ------------------------------------------------------------------
    # Server shutdown
    # ------------------------------------------------------------------

    def test_999_stop_server(self):
        """Stop the Glances web server."""
        print('INFO: [TEST_999] Stop the Glances Web Server')
        pid.terminate()
        time.sleep(1)
        self.assertTrue(True)


class TestGlancesMcpAuthMiddleware(unittest.TestCase):
    """Unit tests for GlancesMcpAuthMiddleware (no server required).

    These tests exercise the middleware directly by constructing ASGI scopes and
    checking whether requests are forwarded to the upstream app or rejected with
    a 401 response.
    """

    # ------------------------------------------------------------------
    # Minimal stubs for the GlancesRestfulApi dependency
    # ------------------------------------------------------------------

    class _Password:
        """Stub GlancesPassword: check_password compares stored == provided."""

        def check_password(self, stored, provided):
            return stored == provided

        def get_hash(self, password):
            # Identity hash — keeps the test logic transparent.
            return password

    class _JwtHandler:
        """Stub JWTHandler that accepts only the literal token 'valid_jwt_token'."""

        is_available = True

        def verify_token(self, token):
            return 'admin' if token == 'valid_jwt_token' else None

    class _Args:
        username = 'admin'
        password = 'secret'  # stored value compared by _Password.check_password

    class _Api:
        args = None  # set per-test
        _password = None  # set per-test
        _jwt_handler = None  # set per-test

    def _make_api(self, with_password=True, with_jwt=False):
        api = self._Api()
        api.args = self._Args()
        api._password = self._Password() if with_password else None
        api._jwt_handler = self._JwtHandler() if with_jwt else None
        return api

    def _make_middleware(self, api, mcp_path='/mcp'):
        upstream_calls = []

        async def upstream(scope, receive, send):
            upstream_calls.append(scope)

        mw = GlancesMcpAuthMiddleware(upstream, api, mcp_path=mcp_path)
        return mw, upstream_calls

    @staticmethod
    def _basic_header(username, password):
        creds = base64.b64encode(f'{username}:{password}'.encode()).decode()
        return [(b'authorization', f'Basic {creds}'.encode())]

    @staticmethod
    def _bearer_header(token):
        return [(b'authorization', f'Bearer {token}'.encode())]

    @staticmethod
    def _make_scope(path, method='GET', headers=None):
        return {
            'type': 'http',
            'path': path,
            'method': method,
            'headers': headers or [],
        }

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _async_collector(bucket):
        """Return an async send callable that appends each message to *bucket*.

        GlancesMcpAuthMiddleware._send_401 uses ``await send(...)``, so the
        send argument must be a coroutine function, not a plain list.append.
        """

        async def _send(msg):
            bucket.append(msg)

        return _send

    # ------------------------------------------------------------------
    # Path routing
    # ------------------------------------------------------------------

    def test_auth_non_mcp_path_passes_through(self):
        """Requests outside /mcp must bypass the auth check entirely."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            responses = []
            await mw(self._make_scope('/api/4/cpu'), None, responses.append)
            return calls, responses

        upstream, responses = self._run(_go())
        self.assertEqual(len(upstream), 1, "Upstream must be called for non-MCP path")
        self.assertEqual(len(responses), 0, "No 401 should be emitted")

    def test_auth_mcp_subpath_is_intercepted(self):
        """Requests to /mcp/sse (sub-path) must be intercepted when auth is active."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            responses = []
            await mw(self._make_scope('/mcp/sse'), None, self._async_collector(responses))
            return calls, responses

        upstream, responses = self._run(_go())
        self.assertEqual(len(upstream), 0, "Upstream must NOT be called without credentials")
        statuses = [r.get('status') for r in responses if isinstance(r, dict)]
        self.assertIn(401, statuses)

    # ------------------------------------------------------------------
    # No-password (open server)
    # ------------------------------------------------------------------

    def test_auth_no_password_mcp_path_open(self):
        """When no password is configured the MCP endpoint is open."""
        api = self._make_api(with_password=False)
        mw, calls = self._make_middleware(api)

        async def _go():
            await mw(self._make_scope('/mcp/sse'), None, lambda _: None)

        self._run(_go())
        self.assertEqual(len(calls), 1, "Upstream must be called when no password is set")

    # ------------------------------------------------------------------
    # Basic Auth
    # ------------------------------------------------------------------

    def test_auth_correct_basic_credentials_pass(self):
        """Valid Basic Auth credentials must reach the upstream."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            scope = self._make_scope('/mcp/sse', headers=self._basic_header('admin', 'secret'))
            await mw(scope, None, lambda _: None)

        self._run(_go())
        self.assertEqual(len(calls), 1, "Upstream must be called with correct credentials")

    def test_auth_wrong_password_rejected(self):
        """Wrong password must return 401."""
        api = self._make_api()
        mw, _ = self._make_middleware(api)

        async def _go():
            responses = []
            scope = self._make_scope('/mcp/sse', headers=self._basic_header('admin', 'wrong'))
            await mw(scope, None, self._async_collector(responses))
            return responses

        responses = self._run(_go())
        statuses = [r.get('status') for r in responses if isinstance(r, dict)]
        self.assertIn(401, statuses)

    def test_auth_wrong_username_rejected(self):
        """Wrong username must return 401."""
        api = self._make_api()
        mw, _ = self._make_middleware(api)

        async def _go():
            responses = []
            scope = self._make_scope('/mcp/sse', headers=self._basic_header('hacker', 'secret'))
            await mw(scope, None, self._async_collector(responses))
            return responses

        responses = self._run(_go())
        statuses = [r.get('status') for r in responses if isinstance(r, dict)]
        self.assertIn(401, statuses)

    def test_auth_no_credentials_rejected(self):
        """Request without any Authorization header must return 401."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            responses = []
            await mw(self._make_scope('/mcp/sse'), None, self._async_collector(responses))
            return calls, responses

        upstream, responses = self._run(_go())
        self.assertEqual(len(upstream), 0)
        statuses = [r.get('status') for r in responses if isinstance(r, dict)]
        self.assertIn(401, statuses)

    # ------------------------------------------------------------------
    # JWT Bearer Auth
    # ------------------------------------------------------------------

    def test_auth_valid_jwt_passes(self):
        """Valid Bearer JWT token must reach the upstream."""
        api = self._make_api(with_jwt=True)
        mw, calls = self._make_middleware(api)

        async def _go():
            scope = self._make_scope('/mcp/sse', headers=self._bearer_header('valid_jwt_token'))
            await mw(scope, None, lambda _: None)

        self._run(_go())
        self.assertEqual(len(calls), 1)

    def test_auth_invalid_jwt_rejected(self):
        """Invalid JWT token must return 401."""
        api = self._make_api(with_jwt=True)
        mw, _ = self._make_middleware(api)

        async def _go():
            responses = []
            scope = self._make_scope('/mcp/sse', headers=self._bearer_header('bad_token'))
            await mw(scope, None, self._async_collector(responses))
            return responses

        responses = self._run(_go())
        statuses = [r.get('status') for r in responses if isinstance(r, dict)]
        self.assertIn(401, statuses)

    # ------------------------------------------------------------------
    # Special cases
    # ------------------------------------------------------------------

    def test_auth_options_preflight_bypasses_auth(self):
        """OPTIONS (CORS preflight) must bypass the auth check."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            scope = self._make_scope('/mcp/sse', method='OPTIONS')
            await mw(scope, None, lambda _: None)

        self._run(_go())
        self.assertEqual(len(calls), 1, "CORS preflight must reach upstream unchecked")

    def test_auth_lifespan_scope_bypasses_auth(self):
        """Non-HTTP lifespan events must bypass the auth check."""
        api = self._make_api()
        mw, calls = self._make_middleware(api)

        async def _go():
            await mw({'type': 'lifespan', 'path': '/mcp'}, None, lambda _: None)

        self._run(_go())
        self.assertEqual(len(calls), 1)

    def test_auth_401_response_has_www_authenticate_header(self):
        """A 401 response must include the WWW-Authenticate header."""
        api = self._make_api()
        mw, _ = self._make_middleware(api)

        async def _go():
            responses = []
            await mw(self._make_scope('/mcp/sse'), None, self._async_collector(responses))
            return responses

        responses = self._run(_go())
        start = next(r for r in responses if isinstance(r, dict) and r.get('type') == 'http.response.start')
        header_names = [name.lower() for name, _ in start.get('headers', [])]
        self.assertIn(b'www-authenticate', header_names)


if __name__ == '__main__':
    unittest.main()
