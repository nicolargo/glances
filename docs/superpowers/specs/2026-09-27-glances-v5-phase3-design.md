# Glances v5 — Phase 3: remote client, browser mode, remaining exporters

**Date:** 2026-09-27
**Branch:** `develop-v5`
**Group:** Phase 3 (`docs/architecture/glances-v5-architecture-decisions.md`
§10): *remote client, all exporters, browser mode, all CVE fixes verified*.
**Revises:** architecture §5 (browser) and §6 (remote client), where noted.

---

## 1. Scope

This is the umbrella design of the phase. It fixes the architecture and the
order of work. Each chantier below gets its own short implementation spec when
it starts, as the Phase 2 groups did.

| In scope | v4 reference |
|---|---|
| Client mode: `-c/--client <host>` shows a remote host in the TUI | `glances/client.py`, `glances_curses.py` (`GlancesCursesClient`) |
| Client credentials: `-u/--username`, `--password`, `[passwords]` | `glances/main.py:429-431`, `password_list.py` |
| Browser mode, in the TUI (`--browser`) and in the Web UI (`-s --browser`, `/browser`) | `client_browser.py`, `servers_list*.py`, `glances_curses_browser.py`, `glances_restful_api.py:552`, `:623` |
| Zeroconf autodiscovery, and `--disable-autodiscover` | `servers_list_dynamic.py` |
| The 18 exporters v5 does not have yet | `glances/exports/glances_*` |
| CVE-2026-32633, -32634 (browser), -30930, -32611, -35588 (SQL/CQL exporters) | architecture §8 |

Out of scope, **dropped by the maintainer (2026-09-27)**:

- The **SNMP fallback** of the client (`--snmp-*`, `--snmp-force`,
  `stats_client_snmp.py`, the SNMP branches of 17 v4 plugins, and the
  `pysnmp-lextudio<6.2` dependency).

---

## 2. Decisions taken with the maintainer (2026-09-27)

| # | Question | Decision |
|---|---|---|
| 1 | How the client reads the server | **One `/api/5/all` poller per server**, like the Web UI does. This revises §6, which had one remote plugin per plugin. |
| 2 | HTTP library | **`requests`**, a single library across v5. The maintainer notes that a client talks to one server at a time, so async HTTP buys nothing. This closes the open question of §6. |
| 3 | SNMP fallback | **Dropped** (§1). |
| 4 | Browser scope | **TUI, Web UI and Zeroconf**, shipped as separate chantiers. |

---

## 3. What v4 does

**Client.**
- `GlancesClient` logs into the server over XML-RPC (`getAll`,
  `getAllViews`) and falls back to SNMP when no Glances answers.
- It feeds `GlancesStatsClient` and runs a `GlancesCursesClient`.
- The server was passive in v4: it collected only when a client asked.
- When the server goes away, the TUI shows `DISCONNECTED`.
- Process actions (cursor, `k`, `+`/`-`) are refused in client mode (#3221).

**Browser.**
- `GlancesClientBrowser` builds its list from two sources: `[serverlist]`
  (static, `server_N_name/alias/port/protocol`, with `protocol` = `rpc` or
  `rest`) and Zeroconf (dynamic, `_glances._tcp.local.`).
- Each server is polled for status and a few `[serverlist] columns`
  (`plugin:field[:key]`).
- Picking a server opens the client, and quitting it returns to the list.
- The Web UI browser is a `/browser` page backed by `/api/4/serverslist`.

**Credentials.**
- `[passwords]` maps a host to a clear password, with an optional `default`.
- v4 hashes the password and **embeds it in the server's `uri`**
  (`http://user:hash@host:port`, `servers_list.py:151`). That URI is what
  `/api/4/serverslist` leaked: CVE-2026-32633.
- Zeroconf entries are untrusted and must not inherit a preconfigured
  password: CVE-2026-32634 (`servers_list.py:130-139`).

---

## 4. Design

### 4.1 D1 — the client is a store filled from `/api/5/all` (decision 1)

```text
glances-v5 -c host
  RemoteSource(host) ──GET /api/5/all──▶ server
        │  every [global] refresh (one request per cycle)
        ▼
  StatsStoreV5  ◀── read by ── TUI, exporters, Python API (unchanged)
```

- **Once, at connection**:
  - `GET /status` checks that the server speaks API 5.
  - `GET /api/5/all/info` fetches every plugin's `fields_description`.
  - `GET /api/5/pluginslist` fetches the plugin list.
- **Each cycle**: one `GET /api/5/all`, and each plugin's payload is written
  to the local store as is, `_levels` included.

**The server's schema drives the client.** The client does not instantiate
its own plugin classes. Some do real work in `__init__` (`ports` starts a
scan thread), and a v5.1 client must display a v5.0 server faithfully. For
each remote plugin, the client builds a lightweight
`RemotePlugin(GlancesPluginBase)` from the server's `fields_description`. It
never calls `_grab_stats`, but it gives the rest of v5 what it expects of a
plugin: `get_export()` for the exporters, `get_api_payload()`, and
`IS_COLLECTION` and the primary key for the TUI.

**Levels and alerts come from the server**, as in v4:
- Cells are coloured from the server's `_levels`, so the client shows the
  server's thresholds, not its own `glances.conf`.
- The alert block mirrors `/api/5/alert` and `/api/5/alert/incidents`.
  They are fetched with `/all` in the same cycle, and a read-only adapter
  gives the TUI the methods it calls on `GlancesAlerts`.
- The client runs no `GlancesAlerts` of its own and therefore **no alert
  actions**. The server is the one that acts.

**Process keys in the client TUI**, per key:

| Key | Behaviour in the client |
|---|---|
| `k`, `+`, `-` | Refused, as in v4 (#3221). Locally they would act on the **client's** PIDs. |
| `e` | Calls the server's `POST /api/5/processes/extended/{pid}`, the pin route the Web UI already uses. |
| `ENTER`/`E` | Filter locally, on the list received. The server's engine filter is global to every client, so it is not touched. |

**Exporters in client mode** (issue #1527) work unchanged, because they only
call `plugin.get_export()`, which the `RemotePlugin` answers from the store.

**Version check.** A server without `/api/5`, such as a v4 server, is
refused at connection with a clear message that names what it found. There
is no v4 compatibility layer.

### 4.2 D2 — transport: `requests`, one session per server (decision 2)

- One `requests.Session` per server, called through `asyncio.to_thread`,
  as the v5 HTTP plugins already are.
- Timeout: `[client] timeout=3` (§6), overridable per server in
  `[serverlist]`.
- The URL scheme follows the argument: `-c https://host:port` works behind a
  TLS reverse proxy, since v5 serves no HTTPS itself. TLS verification is on
  by default, with `[client] ssl_verify` to turn it off or to point at a CA
  bundle.
- **`requests` is a core dependency** (maintainer, 2026-09-27, §6.1): a
  plain `pip install glances` gives a working `-c`, as v4's stdlib XML-RPC
  client did.

### 4.3 D3 — authentication: one token per connection, never a URI

- Credentials come from:
  - `-u/--username` and `--password`, which prompts, as v4 does;
  - otherwise `[passwords] <host>=`, then `[passwords] default=` (static
    entries only, §4.6).
- **A token, not Basic on every poll.** The server checks a password with
  PBKDF2, which is slow by design; Basic credentials every 2 seconds would
  make every client cost the server one PBKDF2 per cycle. The client calls
  `POST /api/5/token` once with Basic, then sends `Authorization: Bearer`,
  which the server checks with an HMAC. On a 401 it takes one new token, and
  then gives up. A server without auth answers 404 on `/token`, and the
  client goes on without credentials.
- **Credentials are never put in a URL** and never kept in any structure that
  gets serialised. They live in the session's auth handler only. This is the
  root of the CVE-2026-32633 fix (§4.5).
- Sending credentials over plain `http://` to a non-loopback host logs a
  WARNING once per server.

### 4.4 D4 — stale data and `DISCONNECTED` (§6, confirmed)

- A failed poll keeps the last payloads in the store and marks the source
  stale. The TUI shows v4's `DISCONNECTED` banner.
- **Revised (maintainer, 2026-09-27, P3-2):** the payloads are never
  cleared. The TUI goes on showing the last values received, and the
  header dates them: `Disconnected from <host> (last update 14:02:31)`.
  `[client] stale_max_cycles` is gone.
- An unreachable server at startup is not fatal: the TUI shows `N/A` and
  the client retries every cycle.

### 4.5 D5 — the browser's server list, and CVE-2026-32633

- **Sources**: `[serverlist]` (static), plus Zeroconf (§4.6) unless
  `--disable-autodiscover` is given.
  - `server_N_protocol` is ignored with a WARNING: v5 speaks REST only.
  - The default port becomes 61208.
- **Polling**: each server gets `GET /status` and the configured `columns`,
  **sequentially** in a background thread, one connection per server at a
  time, in line with decision 2. A server list refresh therefore takes at
  most `servers × timeout`. The list shows the last known values while a
  round is in progress.
- **Picking a server** runs the client (§4.1) in the same process. Quitting
  returns to the list, as in v4.
- **`/api/5/serverslist`** (served with `-s --browser`) returns name, alias,
  port, status, source (static or zeroconf) and the columns. **Never `uri`,
  `username` or `password`**: the list object has no such field to leak.
  A regression test asserts it.

### 4.6 D6 — Zeroconf, and CVE-2026-32634

- **Server side**: `glances-v5 -s` announces `_glances._tcp.local.` with a
  TXT record `api=5`, unless `--disable-autodiscover` is given.
- **Browser side**: it lists only the announcements with `api=5`. A v4
  server is left out, since the client could not talk to it anyway.
- **Credentials** (CVE-2026-32634): a discovered server is untrusted. It is
  sent **no configured credential**: neither `[passwords] default` nor a
  per-host password. Anyone can announce themselves under a trusted
  hostname, so a matching name proves nothing. The user types credentials
  when opening it, and a regression test asserts that nothing is sent
  before.
- `zeroconf` stays an optional extra (`browser`). Without it, the browser
  runs on the static list alone, with an INFO line.

### 4.7 D7 — the Web UI browser page

- `-s --browser` serves `/browser`: a Vue page in the v5 Web UI that lists
  `/api/5/serverslist`, with status and columns, and links to each server's
  own Web UI.
- It reuses the v5 WebUI stack and tokens.
- It is its own chantier, after the TUI browser, because it depends on
  `/api/5/serverslist`.

### 4.8 D8 — the 18 exporters, in five waves

Every exporter:
- keeps v4's configuration section and keys;
- reads only `plugin.get_export()`;
- subclasses `GlancesExportBase` with a synchronous `update()` (§7.3).

| Wave | Exporters | Note |
|---|---|---|
| A — line protocols | graphite, statsd, opentsdb, riemann | Simplest; they set the pattern for the rest. |
| B — message buses | kafka, mqtt, nats, rabbitmq, zeromq | |
| C — document stores | mongodb, couchdb, elasticsearch, clickhouse | |
| D — SQL and CQL | timescaledb, duckdb, cassandra | CVE-2026-30930, -32611 and -35588: every identifier validated or quoted, every value parameterised. The regression tests carry hostile process and mount names. |
| E — the rest | restful (POST), graph (`--export-graph-path`) | `graph` reads the history store (2026-09-26) through a `HistoryStoreV5` read, which answers open question 2 of the history design. |

The waves are independent of each other and of the client: they can run in
any order, or in parallel.

### 4.9 D9 — command line

| v4 option | v5 |
|---|---|
| `-c/--client <host>` | Ported. `host[:port]` or an `http(s)://` URL. |
| `--browser` | Ported, for the TUI; with `-s`, for the Web UI page. |
| `--disable-autodiscover` | Ported, on both the server and the browser side. |
| `-u/--username`, `--password` | Ported, client side (§4.3). |
| `--snmp-*`, `--snmp-force` | Dropped (decision 3). |
| `--cached-time` | **Dropped** (maintainer, 2026-09-27, §6.2): the v5 server always collects, so there is no cache to size. `[<plugin>] refresh` is the v5 lever for server CPU. |

---

## 5. Chantiers, in order

1. **P3-1 client core**: `RemoteSource`, transport and auth (D1 to D3),
   stale data and the banner (D4), the CLI options for `-c`. This is the
   foundation. **Shipped 2026-09-27** (`glances/client_v5.py`);
   `RemotePlugin`, which only exporters need, moves to P3-2 with
   `--export` under `-c`.
2. **P3-2 client TUI**: the mirrored alert block, the process keys (D1), and
   the version check message. **Shipped 2026-09-27**:
   - the last values stay on screen while disconnected, dated in the header
     (D4, revised by the maintainer);
   - `e` pins on the server, `k`/`+`/`-` are refused with a popup, the
     filter applies locally;
   - the alert block is rebuilt from `/api/5/alert` and
     `/api/5/alert/incidents` (`RemoteAlerts`), no local engine, no actions;
   - `--export` under `-c` through `RemotePlugin`; nothing is exported
     while disconnected, so a backend never records the last values twice;
   - the version check shipped with P3-1 (`NotAGlancesV5Server`).
3. **P3-3 exporters, waves A to E** (D8). Independent: they can start at any
   time.
4. **P3-4 TUI browser, static list**: `[serverlist]`, polling,
   `/api/5/serverslist` and CVE-2026-32633 (D5).
5. **P3-5 Zeroconf**: the announcement, discovery and CVE-2026-32634 (D6).
6. **P3-6 Web UI browser page** (D7).
7. **P3-7 CVE verification pass**: every row of §8 marked Phase 3 is checked
   against the code, and §8 is updated. This is the phase's own exit
   criterion.

Each chantier updates the parity inventory and the backlog row it closes.

---

## 6. Open questions for the maintainer — answered 2026-09-27

The maintainer accepted the three proposals.

1. **Is `requests` a core dependency?** **Yes.** Without it, `glances-v5 -c` does not
   work after a plain `pip install glances`, where v4's did. Proposal: make
   it core. It is pure Python, small, and already pulled in by the `cloud`
   and `web` extras.
2. **Drop `--cached-time`?** **Yes.** It sized v4's cache of a passive server, which
   v5 does not have. Proposal: drop it, with a recorded decision, and point
   to `[<plugin>] refresh`, the v5 lever for server CPU.
3. **Client refresh cadence.** The poller runs at the client's
   `[global] refresh` (or `-t`), whatever the server's. Proposal: yes, as in
   v4, where the client paced its own requests. **Yes**, with the
   maintainer's precision: when the server refreshes less often, it answers
   with data it has not refreshed yet. With a client at 2 s and a server at
   4 s, the client gets new data at 2 s and the same data again at 4 s.
   That repeat is normal: only a failed request counts toward
   `DISCONNECTED` (§4.4).
