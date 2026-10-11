# G9-3 — Making the v5 WebUI foundation scale to 34 plugins: Design

**Status:** approved (2026-09-06)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-05-glances-v5-g9-1-webui-serving-design.md`, `2026-09-06-glances-v5-g9-2-webui-foundation-design.md`

---

## 1. Goals

G9-2 built a foundation and its final review found the foundation does not
scale: three architectural gaps that get **32× more expensive** after the next
group lands, plus a fourth the maintainer raised — the rendering is far below
the TUI's information density.

G9-3 settles all four, and re-proves them on the two components that already
exist rather than on new ones.

1. **One request per tick**, not one per plugin.
2. **A plugin registry**, so adding a plugin is a new file, not four edits to a
   central one.
3. **A column model** for collections, so responsive dropping, sorting and
   per-column formatting have a seam instead of 32 hand-written tables.
4. **TUI parity** for `mem` and `network`: same information, same layout logic,
   labels from the same schema.

## 2. Out of scope

- **New plugin components.** G9-3 ships no plugin that G9-2 did not. The point
  is to prove the revised pattern on the two payload shapes that already exist;
  validating it on fresh plugins would test the plugins, not the pattern.
- **Responsive column dropping.** The descriptor carries `priority` (§6) so the
  seam exists; the mechanism waits for a plugin wide enough to need it, and for
  the dimension tokens it would require.
- **Sorting.** Same reasoning: the descriptor makes it possible, `processlist`
  makes it necessary, and neither is in this group.
- **`fetch` timeouts and a staleness indicator.** Real (a black-holed connection
  shows stale numbers indefinitely), but it matters when the UI shows enough
  data for stale values to mislead. Revisit when the plugin count makes the page
  look authoritative.
- **Retiring the v4 Vue app** — Phase 4.

## 3. Decisions taken before design (2026-09-06)

| # | Decision | Consequence |
|---|---|---|
| D1 | Scope is **infrastructure + reworking `mem`/`network`**, no new plugins | The two payload shapes stay the proof; G9-4…N become mechanical |
| D2 | The API **publishes `_key`** in the payload; **labels come from `/api/5/<plugin>/info`** | One new payload field, zero extra per-tick requests, and no client-side inference of the primary key |

## 4. Measured inputs

Captured from a live v5 server, not inferred.

- **`/api/5/all` returns all 26 plugins**, each with its full envelope and
  `_levels`. It already applies the export filter and skips plugins that have
  not published. So the fan-out replacement is a drop-in, not a rewrite.
- **Labels exist but are sparse**: `short_name` / `label` appear in `mem` (3
  fields), `cpu` (3), `sensors` (8). Everything else falls back to the field
  name — which is exactly what `field_label()` already does
  (`glances/outputs/curses_renderer_v5.py:243`).
- **The TUI `mem` block** (`glances/plugins/mem/render_curses_v5.py:16-28`):

```
    MEM    53.2%      active   5.8G
    total  15.3G    inactive   4.4G
    avail   7.2G     buffers   185M
    free    2.6G      cached   4.2G
```

  Eight statistics, a 2-column grid of (label, value) pairs, the title line
  carrying the percent, and an `avail`-vs-`used` switch on whether `available`
  is present in the payload. The G9-2 WebUI component shows **four** stats in a
  vertical list. That gap is the fourth goal.

## 5. One request per tick

`fetchPlugins()` currently issues one `fetch` per plugin per tick. At 34
components and `[global] refresh=2`, every open browser tab issues 17
requests/second against a uvicorn loop that v4 hits once. `Promise.allSettled`
over 34 requests also makes tick latency the slowest endpoint's latency.

G9-3 fetches `/api/5/all` once per tick and slices it per plugin.

**The three-state model is preserved, not weakened.** `/all` omits a plugin
that has not published, so an absent key means "cycle 0, loading" — the same
state the per-plugin `200 null` produced. `validate()` still runs per plugin
against its declared spec, so a wrong-shaped slice is still an error for that
plugin alone, and the other plugins still render. What is lost is per-endpoint
HTTP status, which was never used for anything but the same error state.

## 6. The plugin registry and the column model

### 6.1 Registry

`AppShell.vue` currently names every plugin in four places: the import, the
`components` map, the `PLUGINS` spec list, and the template. Thirty-two ports ×
four edits to one file is thirty-two merge-conflict surfaces, and it
contradicts the project's own rule — prefer discovery mechanisms to hardcoded
lists that require touching a central file for each addition.

A `js/v5/plugins/index.js` exports one array of
`{ name, spec, component }`; the shell renders it with `<component :is>`.
Adding a plugin becomes: one new `.vue` file, one entry.

### 6.2 Column model

`PluginNetwork.vue` hand-writes `<th>`/`<td>` pairs and closes over the literal
`interface_name`. Nothing there gives `containers` or `processlist` a seam.

A collection component declares:

```js
const COLUMNS = [{ field, label, format, priority }];
```

and a shared helper turns it into cells, resolving the tier class through the
payload's `_key` rather than a hardcoded field name.

**This is where D2 pays.** `_levels` for a collection is keyed by the primary
key's VALUE. Without the key's NAME in the payload, every one of 32 components
retypes it — the rule then lives in 32 places instead of the one module the
G9-2 spec said owns tier semantics.

`priority` is declared now and unused now: it is the seam responsive dropping
will need, and adding it later would mean touching every descriptor. Nothing
reads it in this group, and that is deliberate — the alternative is a
half-built dropping mechanism nobody exercises.

**IMPLEMENTATION NOTE:** the shipped descriptor is `{field, format}` only. `label` was dropped in Task 4 (it would have been a second dead-code exception — labels come from the schema via `labelFor`), and `priority` was removed in the final fix wave: the responsive-dropping mechanism this codebase actually uses is an explicit ordered list (`_DROP_ORDER` in `containers`/`processlist` `render_curses_v5.py`), not an integer tier, and the group must carry zero dead code.

## 7. `_key` in the payload

`GlancesPluginBase.get_api_payload()` adds `_key` for collection plugins: the
name of the field carrying each item's identity. Scalar plugins do not get it.

It is shared with the MCP adapter, which reads the same view — harmless there,
and arguably an improvement, since an MCP client faces exactly the same
inference problem.

This is a payload-shape change to a documented API. It is additive (a new
underscore-prefixed key beside `_levels`), so a client that ignores unknown
keys is unaffected, and it belongs in the release notes.

## 8. TUI parity

`mem` and `network` are reworked to match what the TUI already renders:

- **`mem`**: all eight statistics, laid out as the TUI's 2-column grid, percent
  on the title line, and the `avail`-vs-`used` switch driven by whether
  `available` is in the payload.
- **`network`**: the columns the TUI block shows, through the §6.2 descriptor.

**Labels come from the schema, not from the component.** `/api/5/<plugin>/info`
serves `fields_description`; the WebUI fetches it once per registered plugin at
boot (the schema does not change at runtime) and resolves each label with the
same precedence `field_label()` uses: `short_name` → `label` → field name.

That precedence is the contract. Reproducing it means a label improved in the
schema improves both outputs at once, and the 32 remaining ports write no
labels at all.

## 9. Debts folded in

Three G9-2 deferrals that block or tax the next group:

- **Remove the `vue.esm-bundler` alias.** Measured: 61.7 KB of a 192 KB bundle,
  and the compiler is not tree-shaken. Every component is a compiled SFC and no
  `template:` string survives, so it is safe — and the render probe is exactly
  the guard that catches a reintroduction.
- **Make `npm start` serve the v5 app.** The `devServer` block G9-2 added has no
  `/api` proxy and no HTML plugin, so it still serves v4's generated index and
  any `fetch("api/5/…")` 404s. The stated reason for adding it — hot reload for
  32 ports — is not met until this is fixed.
- **Bring `js/v5/**` under eslint.** `eslint.config.mjs` covers `**/*.{ts,vue}`
  only, and eslint is absent from `.pre-commit-config.yaml`, so "hooks pass"
  currently says nothing about the three JS modules.

## 10. Failure modes

| Condition | Behaviour |
|---|---|
| `/api/5/all` unreachable or 5xx | Every plugin shows an error state; the shell and footer still render. This is a real regression in blast radius versus per-plugin fetches, and the honest trade for 34× fewer requests. |
| A plugin absent from `/all` (cycle 0) | Loading state, not an error — same as G9-2's `200 null`. |
| A plugin's slice has the wrong shape | That plugin errors; the others render. Unchanged from G9-2. |
| `/api/5/<plugin>/info` unreachable at boot | Fall back to field names as labels. A missing label must never blank a value. |
| `_key` absent from a collection payload | The component falls back to its declared key field, so an older server still works. |

**IMPLEMENTATION NOTE:** `cellClassFor()` returns no class at all when `_key` is absent, rather than falling back to a declared key field. There is no released v5 server without `_key`, so the fallback would have been an untestable code path; a colourless-but-rendering table is the better call.

## 11. Testing

- `_key` present for collections, absent for scalars; the existing
  `get_export()` / `get_api_payload()` tests unchanged.
- The single-fetch path: one request per tick, a plugin missing from `/all`
  renders loading, a wrong-shaped slice errors only its own plugin.
- The registry: a plugin added to `index.js` renders without editing
  `AppShell.vue` — asserted, not assumed.
- Label resolution follows `short_name` → `label` → field name, and an
  unreachable `/info` degrades to field names.
- `mem` renders all eight statistics, and switches `avail`/`used` on
  `available`'s presence.
- The render probe still returns `childCount: 0` for an empty script and empty
  stderr, and still catches a bundle that renders nothing.
- The colour-literal rule still passes over the new and reworked components.

## 12. Risks

| Risk | Mitigation |
|---|---|
| `/all` makes one failure blank everything | Stated trade (§10). The alternative costs 17 req/s per tab. |
| `priority` is declared and never read — dead code by the project's rule | Named explicitly here as a deliberate seam, with the cost of retro-fitting it stated. If the reviewer disagrees, removing it is cheap; adding it to 32 descriptors later is not. |
| The registry is over-engineered for 3 plugins | It is 3 plugins today and 34 within the group series; the rule it satisfies is the maintainer's own. |
| TUI parity drifts again as plugins are ported | Labels resolve through the schema, and tier semantics through one module. Layout is the part still copied by hand — the honest residual. |

## 13. Deliverables

1. `_key` in `get_api_payload()`, with tests.
2. `/api/5/all` as the single per-tick fetch; per-plugin slicing and validation.
3. `js/v5/plugins/index.js` registry; `AppShell.vue` reduced to rendering it.
4. A column descriptor and a shared cell helper for collections.
5. Label resolution from `/api/5/<plugin>/info`, mirroring `field_label()`.
6. `mem` and `network` reworked to TUI parity.
7. Alias removed, dev server fixed, eslint extended.
8. Release-notes items: `_key` added to the API payload; the v5 WebUI shows
   `mem` and `network` at TUI parity.
