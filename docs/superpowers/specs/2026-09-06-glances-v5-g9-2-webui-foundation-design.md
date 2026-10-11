# G9-2 — v5 WebUI foundation: Design

**Status:** approved (2026-09-06)
**Phase:** 2 (post-`5.0.0a2`) — G9-1 closed the Phase 2 slot; G9-2 is the first step of the UI rewrite
**Sub-project of:** G9 (see G9-1 spec §2.1 for the decomposition)
**Predecessor:** `docs/superpowers/specs/2026-09-05-glances-v5-g9-1-webui-serving-design.md`

---

## 1. Goals

G9-1 made the v5 app serve a page. G9-2 makes that page a foundation the
remaining 32 plugin ports can be built on, without each one re-deciding how to
fetch, how to colour, or how to format.

1. A **service layer** that talks to `/api/5`, validates what comes back, and
   polls at the configured cadence.
2. A **design-token contract** — the named surface every theme, shipped or
   user-written, addresses.
3. An **app shell**: header, plugin area, and a footer alert list.
4. **Two reference plugins**, `mem` and `network`, ported end to end.

`mem` and `network` are not two examples among many. **Scalar and collection are
the only two payload shapes v5 has**, so between them these two establish the
pattern the other 32 follow.

## 2. Out of scope

- **The other 32 plugin components** — G9-3…N, in groups, following this
  group's pattern.
- **Retiring the v4 Vue app.** It keeps running against `/api/4` until the
  Phase 4 cleanup. Both bundles build; neither knows about the other.
- **Browser / multi-server mode** — Phase 3.
- **A JavaScript test runner.** See §9.2: deliberately deferred, with the
  trigger for revisiting it stated rather than left implicit.
- **Shipping more than two themes, or any user-theme loading mechanism.** This
  group fixes the *contract* a theme addresses (§5) so that adding themes later
  is additive. It does not build the loader.

## 3. Decisions taken before design (brainstorming, 2026-09-06)

Recorded because each one binds the 32 downstream ports.

| # | Decision | Consequence |
|---|---|---|
| D1 | The v5 UI is a **redesign**, framed by the TUI v5 decisions — not a repaint of the v4 WebUI | One visual identity across both outputs |
| D2 | Same **semantic tiers and rules** as the TUI; **web-native hues**, not the TUI's ANSI hues | Blue-for-careful and magenta-for-warning are an 8-colour terminal constraint, not a design decision; a browser does not inherit it |
| D3 | **Modern CSS, no framework** | Bootstrap is already half-disconnected in v4 (its SCSS import is commented out at `css/custom.scss:8`), and its components do not serve an interface made of sparklines and dense tables |
| D4 | **User-defined themes are a stated future goal** | The token vocabulary is a public contract, designed now (§5) |
| D5 | **User themes are WebUI-only** | The TUI stays on `dark`/`light`: it is bound by 256 colours and paints on the terminal's own background. "One visual identity" governs the *shipped* themes, not user ones |

## 4. Measured inputs

Captured from a live v5 server, not inferred.

**Scalar (`/api/5/mem`)** — flat fields, plus metadata and levels:

```json
{ "total": 16417853440, "percent": 52.5, ...,
  "time_since_update": 2.011,
  "_levels": { "percent": { "level": "careful", "prominent": true } } }
```

**Collection (`/api/5/network`)** — an envelope; levels keyed by primary key:

```json
{ "data": [ { "interface_name": "wlp0s20f3", "bytes_recv": 1234.5, ... } ],
  "time_since_update": 2.0,
  "_levels": { "wlp0s20f3": { "errors_in": { "level": "ok", "prominent": false } } } }
```

**The v4 components cannot be adapted, only replaced.** `plugin-network.vue`
reads `bytes_recv_rate_per_sec`, `bytes_sent_rate_per_sec` and `bytes_all`.
**None of those fields exists in v5**: the rate fields *are* `bytes_recv` and
`bytes_sent`, converted in place. The envelope is not the only difference; the
field names changed too.

**The TUI colour contract** (`glances/outputs/curses_renderer_v5.py:104-130`),
which D1/D2 align to:

- Four tiers: `ok`, `careful`, `warning`, `critical`.
- `prominent: true` means a **background highlight**, not a different colour.
- **Titles and column headers are never given an alert colour.** The source
  carries this as an explicit instruction: an alert is signalled on the VALUE
  only. This rule is ported verbatim into the web layer.

## 5. The design-token contract

This section is the reason G9-2 exists before G9-3.

A theme is **one block of custom-property values**. Nothing else. `dark` and
`light` are simply the two blocks shipped; `prefers-color-scheme` only selects
which one is the default. Any future source — a config key, a file, an upload —
has to produce such a block and nothing more.

```css
:root { /* dark — the shipped default */ --gl-level-critical: …; }
:root[data-theme="light"] { --gl-level-critical: …; }
```

**Named `dark`/`light`, not `black`/`white`.** `[outputs] theme` already exists
and already takes exactly those two values — default `dark`
(`glances/outputs/glances_curses_v5.py:226`), documented at
`conf/glances.conf:61-63`. A second vocabulary for the same config key would
fragment it, and D1 puts both outputs on one identity. The WebUI reads the same
key and maps its value straight to `data-theme`.

### 5.1 Three rules that make user themes possible

**R1 — No component may contain a colour literal.** A component that writes
`color: #d33` is unthemeable; a user theme cannot reach it. This is not a
convention: it is checked (§9.1). Without enforcement the promise degrades
silently, one plugin at a time, across 32 ports.

**R2 — Light and dark are not special cases.** No scattered
`@media (prefers-color-scheme: dark)` blocks overriding individual rules.
Adding a third theme must mean adding a block, never editing 34 components.

**R3 — Colour is never the only signal of a tier.** Contrast can be verified
for the two shipped themes; it cannot be guaranteed for a user's. A `critical`
value distinguished by hue alone becomes invisible under a badly-chosen theme.
`prominent`'s background highlight — already the TUI's second channel — carries
that load here too.

### 5.2 Contract stability

The token names are an interface from the moment a user writes a theme file.
The set is therefore deliberately **small and semantic** (tier colours,
foreground/background/muted, border, and the typography scale) rather than
per-component. A component needing a new colour uses an existing token or the
set is extended — never renamed.

## 6. Components

| File | Responsibility |
|---|---|
| `js/v5/api.js` | `getJson()`, shape validation, the poll loop. |
| `js/v5/levels.js` | `_levels` → CSS class. The only place tier semantics live. |
| `js/v5/format.js` | Bytes, rates, percentages. Shared by all 34 future components. |
| `css/v5.css` | The token blocks (§5) and the typographic scale. |
| `js/v5/AppShell.vue` | Header, plugin area, footer alert list. |
| `js/v5/PluginMem.vue` | Reference: scalar shape. |
| `js/v5/PluginNetwork.vue` | Reference: collection shape. |
| `js/app_v5.js` | Entry point; mounts the shell. Replaces G9-1's diagnostic body. |
| `webpack.config.js` | v5 config regains `vue-loader` + `VueLoaderPlugin`; gains `devServer` (§8). |

### 6.1 Service layer

Carries G9-1's deferred debt to its close. G9-1's `getJson()` checks
`response.ok`, which stops a 500 being read as data — but a **200 carrying a
valid-but-wrong-shape body** (FastAPI's `{"detail": …}`) still parses, and the
diagnostic page reported a plausible, wrong plugin count.

No status check can catch that. So each plugin declares the shape it expects,
and the service layer rejects a payload that does not match — an error, not
data. Cheap here (two shapes), and the point where it belongs: G9-1's stub was
explicitly the wrong place to build it.

Polling cadence comes from `[global] refresh` via `/api/5/config` — measured in
G9-1: the argument namespace carries no refresh key, so `/api/5/args` is not
its source.

Endpoint outcomes stay independent (`Promise.allSettled`, from G9-1): one
plugin's endpoint failing must not blank the others.

## 7. Failure modes

| Condition | Behaviour |
|---|---|
| One plugin endpoint 5xx or unreachable | That plugin shows an error state; the rest of the page keeps updating. |
| A 200 with an unexpected shape | Treated as an error for that plugin (§6.1), never rendered as data. |
| `/api/5/config` unreachable at boot | Fall back to **2 s** — the value `_DEFAULT_REFRESH_TIME` already uses (`glances/exports/export_base_v5.py:55`) — rather than not polling at all. |
| A plugin has never published (cycle 0) | `/api/5/<plugin>` returns `200 null` (G9-1 contract) — a loading state, not an error. |
| A user theme omits a token | The `:root` default block still supplies it — themes override, they do not replace. |

## 8. Development experience

G9-1 left `npm start` serving the v4 app only: `webpack-dev-server` picks the
config carrying `devServer`, which is `v4Config`. G9-2 gives the v5 config its
own `devServer` block. Without it, G9-3…N develop 32 components with no hot
reload, which is a tax paid 32 times.

## 9. Testing

### 9.1 The token rule is enforced, not documented

A test greps the v5 component sources for colour literals (hex, `rgb(`, `hsl(`,
named CSS colours) and fails on any hit outside `css/v5.css`. R1 is worth
nothing unenforced: it degrades one plugin at a time, and nobody notices until a
user's theme half-works.

### 9.2 Rendering

G9-1's node/DOM probe is extended rather than replaced, and **no npm test
dependency is added**. Its current assertion pins `tagName == "MAIN"`, which
this group's shell replaces — the assertion moves to a durable landmark of the
shell.

**Deferred, with its trigger stated:** a real JS test runner (vitest or
equivalent). Two components with a shared formatter do not justify one. Thirty-
four components with tier logic, formatting and responsive column dropping will.
**The decision point is G9-3**, when the first *group* of plugins lands — not a
vague "later". Deciding it here would be speculative; leaving it unnamed would
make it an oversight.

### 9.3 Behaviour

Service layer: `response.ok` handling, shape rejection, independent endpoint
outcomes, cadence resolution and its fallback. Level mapping: each tier maps to
its class; `prominent` adds the background; **a header never receives an alert
class** (§4). The two components: scalar and collection shapes render, and a
plugin in its cycle-0 `null` state shows loading rather than an error.

## 10. Risks

| Risk | Mitigation |
|---|---|
| The token vocabulary is wrong and 32 ports build on it | Why it is designed now, small, and semantic (§5.2). Extending is additive; renaming is the breaking move, and the contract says renaming is not done. |
| The redesign drifts from the TUI over 32 ports | Tier semantics and the header rule live in ONE module (`levels.js`), not in components. |
| A user theme makes alerts unreadable | R3: colour is never the only signal. |
| Reviewing a UI on HTTP status codes only | The exact G9-1 failure — a blank page every test called success. §9.2 keeps an observed render in the loop. |

## 11. Deliverables

1. `js/v5/api.js`, `levels.js`, `format.js`.
2. `css/v5.css` — token blocks for `dark` and `light`, contrast verified in both.
3. `AppShell.vue`, `PluginMem.vue`, `PluginNetwork.vue`; `app_v5.js` rewritten.
4. `webpack.config.js`: `vue-loader` restored to the v5 config, `devServer` added.
5. Tests per §9, including the token-literal check and the reworked render probe.
6. Release-notes item: the v5 WebUI shows `mem` and `network`; the v4 UI is unchanged.
