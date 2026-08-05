# Glances v5 — G6C design (irq, cloud, mpp)

**Date:** 2026-08-04
**Branch:** `develop-v5`
**Phase:** 2, group **G6C** (order G0→G1→G2→G3→G4A→G4B→G5→G6A→G6B→G6C-amps→**G6C**→G7)
**Status:** design — decisions below are approved; awaiting spec review before plans.

---

## 1. Scope

The last three plugin ports of Phase 2. `amps` was pulled out of this group and
delivered separately (G6C-amps); what remains is `irq`, `cloud` and `mpp`.

After G6C, 34 of 34 portable plugins are on v5. The remainder are deliberate
non-ports: `profiler` (removed in v5), `help` (no longer a plugin), `alert`
(never a plugin — that is G7).

**One spec, three plan files.** The three share no code and each is
independently reviewable and shippable — same shape as G4B (raid/smart/wifi/ip)
and G6B.

All three ship `disable=True` in `conf/glances.conf`. Nothing in this group
changes default behaviour or adds CPU cost to a stock install.

## 2. Out of scope

- Any change to the six plugins that override `_derived_parameters()` and
  therefore return `{}` from `/api/5/<plugin>/limits`. None of the three
  plugins here overrides it, so G6C does not widen that known limitation
  (see the `/limits` design, §4.6).
- Export modules and the FastAPI-served WebUI — the two Phase 2 slots that
  follow G7.

---

## 3. `irq`

Linux-only collection over `/proc/interrupts`. Primary key `irq_line`, one
numeric field `irq_rate`. `irq_rate` is **not** `watched`: v4 defines no
thresholds for this plugin, so there is nothing to colour or alert on.

**Rate computation moves to the base class.** v4 computes the per-second rate by
hand with `getTimeSinceLastUpdate` (`glances/plugins/irq/__init__.py`). v5
declares `"rate": True` on `irq_rate` and lets `GlancesPluginBase` divide by
`time_since_update` — that machinery exists precisely for this, and the manual
arithmetic disappears.

**Behaviour to preserve verbatim:**

- non-Linux → empty collection, no exception, no log spam
- sort by `irq_rate` descending
- **top 5 only** (`stats[:5]` in v4) — this is a display *and* data cap in v4;
  keep it at the data layer so REST and TUI agree

**Not carried over:** v4 exposes a CLI switch spelled `enable_irq` rather than
`disable_irq` — the only plugin with inverted polarity. v5 has no per-plugin CLI
switches at all (`main_v5.py` defines only `--enable-mcp` and
`--disable-config-exec`); enablement is config-only, via `DISABLED_BY_DEFAULT`
plus `[irq] disable=`. The quirk therefore disappears with nothing to replace
it.

**TUI:** right-hand sidebar (v4 `glances_curses.py:124`).

`EMITS_ALERTS = False` — v4 defines no thresholds for this plugin.

---

## 4. `cloud`

Scalar plugin exposing the cloud instance the host runs on: `platform`, `id`,
`name`, `type`, `region`.

### 4.1 One-shot async fetch, cached for the process lifetime

v4 spawns two daemon threads (`ThreadOpenStack`, `ThreadOpenStackEC2`). Their
`run()` docstring claims an "Infinite loop, should be stopped by calling the
stop() method", but the body has no loop: it walks the metadata keys once and
returns. The threads die immediately. Cloud metadata is static, so this is the
correct behaviour with a misleading implementation.

v5 drops both thread classes and implements the real semantics directly:

```python
async def _grab_stats(self) -> dict:
    if self._fetched:
        return self._cached
    self._fetched = True
    self._cached = await asyncio.to_thread(self._probe_sync)
    return self._cached
```

`_fetched` is set **before** awaiting, so a failed probe is not retried on every
cycle — matching v4, where a dead thread never retries either.

**Probe order:** vanilla OpenStack first; EC2 only if vanilla returned nothing.
This mirrors v4's `update()` (`stats = self.OPENSTACK.stats; if not stats:
stats = self.OPENSTACKEC2.stats`) and is cheaper than v4, which always ran both
threads.

| | vanilla OpenStack | OpenStack EC2 |
|---|---|---|
| `platform` | `OpenStack` | `Amazon EC2` |
| URL | `http://169.254.169.254/openstack/latest/meta-data` | `http://169.254.169.254/latest/meta-data` |
| `id` | `project_id` | `ami-id` |
| `name` | `name` | `instance-id` |
| `type` | `meta/role` | `instance-type` |
| `region` | `availability_zone` | `placement/availability-zone` |

Each value is a path appended to the URL (`{URL}/{value}`), and the response
body becomes the field value. The maps are copied verbatim from v4's
`OPENSTACK_API_METADATA` class attributes; the implementation must not
re-derive them.

`platform` is set only when **every** key of a map resolved. This is
**stricter than v4 on purpose**, not parity: v4's `for…else` breaks out only in
its `except Exception` clause, so a plain non-ok response (a 404) merely skips
that key, the loop completes, the `else` still fires and `platform` *is* set —
with a genuinely partial dict that reaches `/api/4/cloud`. v5 discards the
whole provider on any non-ok response, which is what §4.2's "publish `{}`" rule
keys off and what closes the #2485 partial-payload leak at the data layer.

**Each provider is its own failure domain.** An exception raised while probing
one provider must be caught *within* that provider's probe and treated like a
non-ok response — the next provider is still tried. Scoping the handler around
the whole provider loop would mean a single transient timeout on OpenStack
permanently prevents EC2 detection, since `_fetched` is latched on the first
cycle. v4 gets this for free by running the two probes in independent threads.

### 4.1b HTTP client — `requests` behind `asyncio.to_thread`

`httpx` was considered and **rejected** for this plugin.

`requests` is already the de-facto HTTP client of v5 plugin code: `ports`
drives the reused v4 `ThreadScanner._web_scan` through `asyncio.to_thread`,
`containers` reaches Docker through the v4 engine, and the `nginx` AMP uses it
directly. `httpx` is present only as a transitive dependency of FastAPI's
`TestClient` — no v5 code imports it, and it is declared nowhere as a runtime
dependency. Adopting it here would have made `cloud` the only v5 plugin using
it and would have required declaring a new dependency, which is the opposite of
consolidation. The `cloud` extra therefore stays `["requests"]` and
`pyproject.toml` is not touched.

`requests` blocks, and on bare metal — the common case — the probe burns four
3-second timeouts. `asyncio.to_thread` keeps that off the event loop, the same
pattern `ports`, `npu`, `mpp` and `irq` already use. The cost is paid once at
startup, never per cycle.

**Deferred, not settled.** Architecture §6 commits the Phase 3 remote client to
`httpx async`, and that remains the right call there: it polls N servers every
cycle, which is where async HTTP actually pays. The choice of a single client
library for v5 is therefore an **open question to reopen at the start of
Phase 3**, with the full picture — by then it will be clearer whether
`requests` can be dropped from the graph at all, since the Docker engine and
the nginx AMP still pull it in. Nothing in this design constrains that
decision.

### 4.2 Failure and display

Any failure — timeout, connection refused, non-2xx, missing `httpx` — yields an
empty dict. The plugin then renders nothing, exactly as v4.

v4 additionally suppresses display when `platform` or `name` is missing
(issue #2485). Keep that, but move it to the **data layer**: if the probe cannot
establish `platform`, publish `{}` rather than a partial dict. A partial payload
would otherwise reach `/api/5/cloud` even though no UI shows it.

**TUI:** header slot, next to `uptime` (v4 `glances_curses.py:720-726`). The
header-slot mechanism has existed since G1.

### 4.3 Security — hard-coded endpoint

The plugin issues requests to the link-local metadata address `169.254.169.254`.
CVE-2026-35587 hardened the `ip` plugin specifically against reaching cloud
metadata IPs; here that address is the intended destination.

**The URLs are hard-coded and MUST NOT become configurable.** No config key may
influence the host, scheme, port or path. This closes the SSRF class by
construction, the same way the closed key space closes the config-leak class in
the `/limits` design (§7 there). A future request to "make the endpoint
configurable" is a request to reintroduce an SSRF, and must be refused.

`EMITS_ALERTS = False`.

---

## 5. `mpp`

Collection of Rockchip Media Process Platform engines (RKVENC, RKVDEC,
RKJPEGD). Primary key `engine_id`; fields `name`, `type`, `load`,
`utilization`, `sessions`.

### 5.1 Engine reuse

`glances/plugins/mpp/cards/rockchip_mpp.py` is reused **as is**, exactly as
`glances/plugins/npu/model_v5.py` imports `glances.plugins.npu.cards.*`.
`model_v5.py` is a thin projection calling `get_stats()` through
`asyncio.to_thread`.

The one exception is §5.2 — the only edit this group makes to a v4 file.

### 5.2 DECISION — stop writing to `/proc`

**Approved: remove the write.**

v4's `_ensure_load_interval()` (`rockchip_mpp.py:66-80`, called from
`get_stats()` at `:100`) reads `/proc/mpp_service/load_interval` and, when it
finds `0`, **writes** `1000` into it. A monitoring tool must not mutate kernel
state: the setting is global and affects every other reader of that file.

Delete: the method (`:66-80`), the `_load_interval_set` attribute (`:51`), the
`_LOAD_INTERVAL_MS` constant (`:40`), and the call site (`:100`).

**Consequence — the plugin goes silent, not merely degraded.** `_parse_load()`
is the *sole* source of engines: `get_stats()` builds its list only from
`/proc/mpp_service/load`. With `load_interval == 0` that file is empty,
`_parse_load()` returns `{}`, and the plugin publishes `[]`. An operator who
enables `mpp` without the manual step sees nothing at all.

Two mitigations are therefore part of this design, not optional polish:

**(a) `docs/aoa/mpp.rst` — prerequisite at the top of the page**, before the
config block, not a footnote:

```sh
# Required once per boot, as root. Without it the kernel reports no load
# and the plugin displays nothing.
echo 1000 > /proc/mpp_service/load_interval
```

Include a pointer to making it persistent (systemd unit or equivalent).

**(b) A single startup WARNING.** When the plugin is enabled and the load file
is empty, log a WARNING **once per process** naming the file and the exact
command. Without it, the degraded mode is indistinguishable from a bug and the
maintainer receives the issue report. This follows the "visible but non-fatal
startup warning" rule of the project's security philosophy.

The WARNING lives in `model_v5.py`, not in the reused card: the card stays a
dumb reader, and the "once per process" latch belongs to the plugin instance.

### 5.3 Branch impact

`rockchip_mpp.py` is a v4 file, but merges only ever flow `develop →
develop-v5`, never back. This edit therefore does not reach v4 users. It lands
in `develop` only at the eventual `develop-v5 → develop` merge at the 5.0.0
release candidate, by which point it is v5 behaviour. **Not** a v4 breaking
change.

If `develop` later touches `rockchip_mpp.py`, the weekly merge will conflict on
this hunk; resolve in favour of develop-v5 (no write).

**TUI:** `_top` block, between `npu` and `gpu` (v4 `glances_curses.py:110`).

`EMITS_ALERTS = True` — `conf/glances.conf` already ships
`load_careful=50 / load_warning=70 / load_critical=90` under `[mpp]`.

---

## 6. Cross-cutting

- **Snap confinement:** the reused v4 engines already wrap `open()` inside
  `try`, not just the read. Nothing to fix; do not "improve" it.
- **`/limits`:** none of the three overrides `_derived_parameters()`, so all
  three report their thresholds correctly through `get_limits()`.
- **`NEWS.rst` is not touched.** The `mpp` `/proc` change and the `requests` →
  `httpx` move are release-note material, recorded here for the maintainer to
  pick up at release time.

## 7. Tests

Per plugin, following the group conventions already in `tests/`:

**`irq`** — parse a `/proc/interrupts` fixture; non-Linux yields `[]` without
raising; sort order is by rate descending; the 5-item cap holds; `rate` is
computed by the base class (two cycles, known `time_since_update`).

**`cloud`** — vanilla OpenStack success; vanilla empty then EC2 success; both
failing yields `{}`; a partial response missing `platform` publishes `{}` and
not a partial dict; **a second cycle issues no HTTP request at all** (the
one-shot cache is the core claim); missing `httpx` degrades to `{}`. HTTP is
mocked — no test may touch the network.

**`mpp`** — parse a `/proc/mpp_service/` fixture; thresholds resolve on `load`;
absent `/proc/mpp_service` yields `[]`; **an empty load file yields `[]` and
logs the WARNING exactly once across repeated cycles**; and a regression test
asserting `rockchip_mpp.py` performs **no write** — the file is opened read-only
on every path.

## 8. Deliverables

- `glances/plugins/irq/model_v5.py` + `render_curses_v5.py`
- `glances/plugins/cloud/model_v5.py` + `render_curses_v5.py`
- `glances/plugins/mpp/model_v5.py` + `render_curses_v5.py`
- edit: `glances/plugins/mpp/cards/rockchip_mpp.py` (remove the `/proc` write)
- edit: `docs/aoa/mpp.rst` (prerequisite section)
- three plan files under `docs/superpowers/plans/`
