# Glances 4.5.9 vs Glances 5.0.0

Glances 5 is a complete rewrite of the monitoring engine, the REST API, the
terminal UI and the Web UI. This page compares the current stable release
(**4.5.9**) with the first beta of version 5 (**5.0.0**).

> **Beta notice.** 5.0.0 is a pre-release. Glances 4 keeps receiving bugfix
> and security releases on the `support/glancesv4` branch, so you can migrate
> at your own pace.

## At a glance

- **A new collection engine.** An asyncio scheduler collects each plugin at its
  own refresh rate into a shared store, read by the TUI, the REST API, the
  exporters and the MCP server.
- **One protocol.** Everything goes through the REST API: no more XML-RPC or
  SNMP fallback.
- **Secure by default.** Loopback binding, stronger password hashing, hardened
  HTTP headers, DNS-rebinding protection and a full security audit.
- **Richer history and alerts.** Server-side history (1200 points by default),
  a new alerts engine and a redesigned Web UI.
- **Lighter TUI.** About 17 % less memory than v4 in our measurements.

## Performance

Measured on a 4-vCPU Linux container, Python 3.13, psutil 7.2.2, idle machine,
default 2 s refresh. CPU and memory are averaged over 60 s; startup is the mean
of 5 runs. These are indicative figures, not a statistical benchmark.

| Metric | Glances 4.5.9 | Glances 5.0.0 | Difference |
|---|---|---|---|
| Server startup (`glances -w`, until first API answer) | 0.60 s | 0.55 s | Comparable (-8 %) |
| TUI startup (first screen) | 0.36 s | 0.25 s | -30 % (single run) |
| Memory, TUI (RSS) | 55 MB | 46 MB | **-17 %** |
| Memory, server + Web UI (RSS) | 65 MB | 63.5 MB | Comparable |
| CPU, TUI | 1.4 % | 1.4 % | Same |
| CPU, server with an active Web UI client | 1.7 % | 1.6 % | Same |
| CPU, server with no client | 0.2 % | 0.8 % | Higher: v5 collects continuously (tunable with `[<plugin>] refresh`) |
| Installed size (virtualenv) | 44 MB | 45 MB | Same |

**Takeaway:** startup time and resource usage are on par with v4, with a clear
memory gain in the TUI. The main benefits of v5 are architectural, functional
and security-related.

## Features

| Area | Glances 4.5.9 | Glances 5.0.0 |
|---|---|---|
| Collection | On demand, `--cached-time` | asyncio scheduler, per-plugin refresh rate, shared stats store |
| Client/server | XML-RPC (port 61209) and SNMP | REST only (port 61208); `-s` and `-w` are equivalent, `-c` connects the TUI through the API |
| REST API | `/api/4` | `/api/5`, new data model, stricter routes (unknown field returns 404) |
| History | Per-field history routes | Columnar `{timestamps, series}` history, 1200 points by default |
| Alerts | Legacy engine | New alerts engine, alert list in the Web UI |
| Web UI | Vue.js | New Vue 3 Web UI, history curves colored by threshold level |
| TUI | Legacy curses UI | New curses TUI |
| Export modules | 26 files, historical base classes | 24 modules sharing a single `export_base` |
| MCP server | Beta | Yes, backed by the shared store |
| Startup network calls | PyPI update check | None |
| Codebase | ~33,900 lines of Python | ~39,800 lines of Python, 161 test files |

## Security

Glances 5 includes the fixes of a post-cutover security audit (2026-10-17).

| Topic | Glances 4.5.9 | Glances 5.0.0 |
|---|---|---|
| Default bind address | `0.0.0.0` | `127.0.0.1` |
| DNS-rebinding protection | Optional | On by default for loopback servers |
| Password hash | Legacy format | PBKDF2-SHA256, 600,000 iterations |
| `/api/5/config`, `/api/5/args` without password | n/a | Only the keys the Web UI needs |
| HTTP headers | Defaults | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`; cross-site POST refused |
| Command substitution in config values | Backticks supported | Removed (CVE-2026-33641) |
| JWT | n/a | Secret of 32+ characters, `exp` and `iat` required, expiry capped to a day |
| Client mode (`-c`, `--browser`) | n/a | Server answers capped at 32 MiB, with a global deadline |
| Exporters | n/a | InfluxDB TLS verified, Graphite/StatsD paths filtered, CSV formula injection prevented |
| Zeroconf | n/a | Loopback, link-local and reserved announcements ignored, at most 256 servers followed |
| `--fetch-template` | n/a | Rendered in a Jinja2 sandbox |

## What changes when you migrate

- A Glances 5 client cannot talk to a Glances 4 server, and the reverse.
- API clients must move from `/api/4` to `/api/5`.
- Threshold keys in the configuration file were renamed without aliases
  (for example `rx_*` becomes `bytes_recv_*`).
- Password hashes must be regenerated with `glances --set-password`.
- `--fetch` templates written for v4 must be updated.
- Removed options: `-P/--plugins`, `--cached-time`, `--disable-check-update`,
  the SNMP options, `--sparkline`, `--trace-malloc`,
  `--enable-process-extended`.
- A server now listens on `127.0.0.1` only: use `-B 0.0.0.0` or
  `[outputs] bind_address` to expose it. The Docker images are already
  configured for this.

See `NEWS.rst` for the complete list of changes.

## Try it

```bash
python3 -m venv ~/.venv-glances5
source ~/.venv-glances5/bin/activate
pip install --pre --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ 'glances[web]>=5.0.0b1'
glances --version
```
