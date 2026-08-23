# Glances v5 — G8-5 design: three export-related features

**Status:** Approved — ready for `writing-plans`
**Date:** 2026-08-23
**Branch:** `develop-v5`
**Predecessor:** G8-1 (export base + scheduler loop + CLI, staged), then G8-2/3/4 (six exporters)
**Successor:** G9 — WebUI served by FastAPI

Closes three long-standing issues that the iso-v4 port deliberately left alone:

| Issue | Title | State entering G8-5 |
|---|---|---|
| [#1527](https://github.com/nicolargo/glances/issues/1527) | Export while in server mode | **Already implemented by G8-1** — only the documentation duty remains |
| [#3211](https://github.com/nicolargo/glances/issues/3211) | Use `get_export()` in the API | Not implemented; scope is smaller in v5 than in v4 (§2.2) |
| [#3423](https://github.com/nicolargo/glances/issues/3423) | `result_float` field in AMPs for InfluxDB | Not implemented; v4 has a comment promising a field its code never creates |

---

## 1. Goals

1. Record and document that export now runs in every mode (#1527), including the
   CPU-baseline warning architecture §7.1 makes mandatory.
2. Make `/api/5/<plugin>` and `/api/5/all` serve the export-filtered view rather
   than the raw store payload (#3211), **without** stripping `_levels`.
3. Give the AMP plugin a real `result_float` field so a numeric AMP result
   reaches InfluxDB as a number rather than only as a string (#3423).

## 2. What each issue actually means in v5

### 2.1 #1527 — already done

G8-1 wires the exporters in `main_v5.assemble()` at lines 491-493, **before** the
`if args.server:` branch at line 501. Both TUI mode and `-s` server mode
therefore register and drive exporters. The v4 limitation the issue describes —
a server that only exports when a client connects — cannot exist in v5, because
the asyncio scheduler polls plugins on their own cadence regardless of who is
connected (architecture §7.1).

Client mode is out of scope: `GlancesPluginRemote` does not exist until Phase 3.
When it lands, export must be verified there too; §5 records that as the one
open edge of this issue.

**Remaining work is documentation only** — see §3.1.

### 2.2 #3211 — the scope shrank between v4 and v5

The issue asks the REST API to serve `get_export()`, which in v4 filters through
each plugin's `export_exclude_list`.

Two facts change what that means in v5:

- **v4's `export_exclude_list` is used by exactly two plugins**: `containers`
  (`['cpu', 'io', 'memory', 'network']`) and `vms` (an empty list, i.e. nothing).
- **Those four `containers` fields do not exist in v5.** They were nested
  sub-dicts in v4 — which is precisely why they exported badly and were
  excluded. The G6A port flattened them into scalars (`cpu_percent`, `io_rx`,
  `io_wx`, `network_rx`, `network_tx`, `memory_usage`, `memory_percent`, …).
  The problem was solved structurally; there is nothing left to exclude.

So porting v4's exclusions is a **no-op**, and today the only field the filter
removes is `time_since_update` (the sole `exportable: False` declaration in the
codebase, in `_BASE_METADATA_FIELDS`).

That does not make the issue empty. Its value in v5 is **structural**: the API
stops being able to expose a field a plugin has marked non-exportable, and every
future plugin gets the lever for free. No existing field disappears from any
payload, so despite the issue's `breaking change` label — which described the v4
situation — **this change breaks no user's dashboard**. §3.2 records why.

A wider audit (marking descriptive strings like `containers.command`,
`containers.created`, `containers.id` non-exportable) was considered and
**rejected for this cycle**: each such field is a column that would vanish from
an existing dashboard, which is a real cost for no user-visible gain.

### 2.3 #3423 — v4's comment describes a field v4 never creates

`glances/exports/export.py::normalize_for_influxdb` carries:

```python
# Some fields should be converted to string in order to avoid type mismatch in InfluxDB
# Example: the 'result' field of the AMP plugin can be a string or a number depending on
# the AMP implementation. In this case, we convert it to a string and create another field
# with the same name but with a suffix (_float) to keep the original value.
# See #3419 for more details.
FIELD_TO_STRING = ["result"]
```

The code then does only `fields[k] = str(fields[k])`. **No `_float` field is
ever created**, in v4 or in v5 (the v5 port is verbatim, by design). A numeric
AMP result — an exit code, a queue depth, a temperature — reaches InfluxDB as
the string `"42"`, unusable in a numeric query. That is the gap #3423 names.

---

## 3. Design

### 3.1 #1527 — documentation

`docs/gw/index.rst` gains a short section, in the page's existing voice:

- Export runs in **standalone and server mode** alike. A headless
  `glances -s --export influxdb2` is a supported, first-class deployment; no
  client needs to connect.
- **Server mode costs more CPU at rest than v4 did.** v4's server collected
  lazily, on client request; v5's scheduler polls every plugin on its own
  cadence whether or not anyone is watching. The mitigation is `refresh`:
  `[global] refresh` for the baseline, `[<plugin>] refresh` for expensive
  plugins, `[export] refresh` for the export flush itself. Point at
  `DEFAULT_REFRESH_TIME` as the reason most plugins already poll slower than
  the global rate.

No code change. The `[export] refresh` key documented in `conf/glances.conf` by
G8-1 is referenced here rather than re-explained.

### 3.2 #3211 — a third payload view

`GlancesPluginBase` currently offers two views:

| Method | Strips `_*` | Strips `exportable: False` | Consumer |
|---|---|---|---|
| `get_stats()` | no | no | REST (today), MCP |
| `get_export()` | yes | yes | export modules (G8-1) |

G8-5 adds the third, which is the one the REST API should have been serving:

```python
def get_api_payload(self) -> dict[str, Any]:
    """Filtered view for the REST API and MCP (issue #3211).

    Strips fields declared `exportable: False`, and keeps `_levels`.
    Always a dict — a collection plugin keeps its store envelope.
    """
```

Note the return type: **always a dict**, unlike `get_export()`, which returns a
bare `list` for collections. The API's job is to serve the payload shape clients
already know, envelope included.

**Why `_levels` stays.** It is not a measurement — it is a computed view of one,
and it is what a UI colours cells from. Stripping it would be defensible in a
metrics backend (where it is noise, and where G8-1's `get_export()` correctly
drops it) and indefensible in the API, whose main consumer is about to be the
WebUI (G9). A WebUI forced to fetch levels from a second route would pay an
extra HTTP round-trip per refresh for nothing.

Implementation: factor the projection already inside `get_export()` into one
private helper parameterised by whether internal keys survive, so the two public
views cannot drift:

```python
def _project(self, d: dict, *, keep_internal: bool) -> dict:
    return {
        k: v
        for k, v in d.items()
        if (keep_internal and k.startswith("_"))
        or (not k.startswith("_") and self._fields.get(k, {}).get("exportable", True))
    }
```

`get_export()` calls it with `keep_internal=False`, `get_api_payload()` with
`keep_internal=True`.

**Collection plugins need care here, and the trap is easy to fall into.** Their
store payload is `{"data": [item, ...], "time_since_update": ..., "_levels": {...}}`.
Running `_project()` over that top-level dict alone would treat `"data"` as a
field name — it is absent from `fields_description`, so `.get("exportable", True)`
returns True and the whole list survives **unprojected**, with every item's
non-exportable fields intact. `get_api_payload()` must therefore project the
envelope AND map `_project()` over each item inside `data`:

```python
if self.IS_COLLECTION:
    payload = self.store.get(self.plugin_name, {})
    out = self._project(payload, keep_internal=True)
    out["data"] = [self._project(item, keep_internal=True) for item in payload.get("data", [])]
    return out
```

`get_export()` sidesteps this only because it discards the envelope entirely.

**Routes changed** (`glances/routes_v5.py`):

- `GET /api/5/{plugin_name}` — was `store.get(plugin_name)`, becomes the
  resolved plugin's `get_api_payload()`. The "registered but nothing published
  yet" case still returns JSON `null`, distinct from a 404.
- `GET /api/5/all` — was `store.as_dict()`, becomes a comprehension over the
  registered plugins' `get_api_payload()`, **skipping empty payloads**. The
  skip is not an optimisation: `tests/test_routes_v5.py::test_all_excludes_unwritten_plugins`
  pins the existing contract that a registered-but-never-updated plugin is
  ABSENT from `/all`, not present with an empty body. A naive comprehension
  would flip that and break a client's "is this plugin live?" check.

**MCP** (`glances/outputs/mcp_adapter_v5.py:97` and `:165`) reads the store
directly for the same two shapes. It moves to `get_api_payload()` too — an MCP
client is a consumer like any other, and leaving it on the raw payload would
recreate the inconsistency the issue is about.

**What does NOT change:** the TUI reads the store directly and is untouched;
`/api/5/{plugin}/limits`, `/info`, `/alert` and `/config` are untouched.

### 3.3 #3423 — `result_float` as a declared AMP field

The field is declared in the AMP plugin, not synthesized in the InfluxDB
normaliser:

```python
"result_float": {
    "description": "Numeric value of `result` when it parses as a number, else None.",
    "unit": "number",
},
```

filled in `_grab_stats()` beside `result`:

```python
"result": amp.result(),
"result_float": _as_float(amp.result()),
```

where `_as_float` returns `float(value)` or `None` on `TypeError`/`ValueError`.

**Why the plugin and not the exporter.** v5's rule is that the export layer
shapes data, it does not invent it (architecture §7.2: `get_export()` is the
only permitted access path, and exporters transform rather than compute). A
field synthesized inside `normalize_for_influxdb()` would be invisible to CSV,
JSON, Prometheus and the API, and it would break the verbatim-port property that
G8-1's review confirmed branch for branch — the single strongest guarantee we
have that dashboards keep working.

Declaring it as a field means it flows everywhere: InfluxDB gets a numeric
field, Prometheus gets a gauge it can actually scrape (its `export()` drops
non-numeric values, so `result` was silently absent there), the REST API and the
WebUI get it, and CSV gains one column.

`FIELD_TO_STRING = ["result"]` in `normalize_for_influxdb()` is **not touched**:
`result` stays a string for the type-mismatch reason #3419 documents, and
`result_float` carries the number beside it. That is exactly what v4's comment
promised.

`None` for a non-numeric result is deliberate: `normalize_for_influxdb()`
already skips `None` fields (`if fields[k] is None: continue`), so a text-only
AMP contributes no numeric series rather than a misleading `0.0`.

---

## 4. Out of scope

- Any wider `exportable: False` audit of the 34 plugins (§2.2).
- Export in **client** mode — `GlancesPluginRemote` is Phase 3 (§2.1).
- Touching v4 code, including the misleading comment in
  `glances/exports/export.py`. v4 stays read-only until the Phase 4 cleanup.
- Changing `/api/5/{plugin}/limits`, `/info`, `/alert`, `/config`.

## 5. Risks

| Risk | Mitigation |
|---|---|
| `/api/5/all` moves from a store read to a registry read | The existing contract — a plugin that has never published is ABSENT, not empty — is pinned by `test_all_excludes_unwritten_plugins` and must be preserved by skipping empty payloads. Verified against that test, which is not to be edited. |
| The WebUI (G9) turns out to need a field this filter removes | Only `time_since_update` is removed today, and `_levels` is deliberately kept. G9 is written after this and will surface any gap immediately. |
| `result_float` is a new field in a payload dashboards parse | Additive only — no existing field changes name, type or value. |
| An AMP returning a numeric-looking string (`"007"`) now also exports `7.0` | Intended: that is the numeric value the issue asks for. `result` keeps the original string. |
| The `_project()` refactor changes `get_export()` behaviour | G8-1's export tests cover `get_export()` directly; they must stay green untouched, which is the regression guard. |

## 6. Deliverables

1. `docs/gw/index.rst` — the all-modes statement and the CPU-baseline warning.
2. `GlancesPluginBase._project()` + `get_api_payload()`, with `get_export()`
   refactored onto the shared helper.
3. `glances/routes_v5.py` — `/api/5/{plugin}` and `/api/5/all` serve the filtered view.
4. `glances/outputs/mcp_adapter_v5.py` — same two shapes.
5. `glances/plugins/amps/model_v5.py` — `result_float` declared and filled.
6. Tests: the filtered view (both shapes, `_levels` kept, `exportable: False`
   removed), the two routes, the MCP resources, and `result_float` for numeric,
   non-numeric and `None` AMP results.

No `NEWS.rst` entry — the maintainer writes the changelog at release time. The
three issue numbers and the `/api/5` payload change are recorded here for it.
