# Skill: Glances v5 — Configuration (`GlancesConfigV5`)

Use the v5 configuration loader (`glances.config_v5.GlancesConfigV5`) for any
new code in `develop-v5`. The v4 module `glances.config` is kept untouched
during the transition.

## Loading priority (ascending)

Each layer **overlays specific keys** onto the previous one — layers are not
replaced in bulk. This is a deliberate behaviour change vs. v4
(first-found-wins).

| # | Source | Notes |
|---|---|---|
| 1 | `GlancesConfigV5.DEFAULTS` (class attribute) | Hardcoded baseline. Phase 0 keeps this minimal; each phase adds the keys it references. |
| 2 | `/etc/glances/glances.conf` | System administrator baseline. |
| 3 | `$XDG_CONFIG_HOME/glances/glances.conf` | Falls back to `~/.config/glances/glances.conf` when XDG is unset. |
| 4 | `$GLANCES_CONFIG_FILE` | Single file pointed to by env var. |
| 5 | `-C <path>` (CLI flag) | Overrides `$GLANCES_CONFIG_FILE`. |
| 6 | `GLANCES_<SECTION>__<KEY>=value` env vars | **Highest priority.** Container/Kubernetes overlay. |

### Environment variable rules

- Prefix: `GLANCES_`
- Separator: **double underscore `__`** between section and key
- **Section names contain no underscores** by convention
  (`serverlist`, not `server_list`). Keys may contain any number of
  underscores.
- Section and key are lowercased before lookup.
- An env var without `__` is silently ignored.

Examples:

```bash
GLANCES_GLOBAL__REFRESH_TIME=5
GLANCES_MEM__CRITICAL_ACTION="echo critical"
GLANCES_OUTPUTS__API_DOC=false
```

## Typed accessor

The type is inferred from the `default` argument — you never pass a type
explicitly.

```python
config = GlancesConfigV5()

refresh: int   = config.get("global",  "refresh_time", 2)
api_doc: bool  = config.get("outputs", "api_doc", True)
hosts:  list   = config.get("outputs", "webui_allowed_hosts", [])
host:   str    = config.get("influxdb", "host", "localhost")
ratio:  float  = config.get("foo", "ratio", 1.0)
```

Supported types: `str`, `int`, `float`, `bool`, `list[str]`. `dict` is not
supported — complex structures belong in dedicated config sections.

### Bool parsing

Accepted truthy values (case-insensitive): `1`, `true`, `yes`, `on`.
Accepted falsy values: `0`, `false`, `no`, `off`. Anything else raises
`ValueError`.

### List parsing

Comma-separated, whitespace-stripped, empty entries dropped:

```ini
[outputs]
webui_allowed_hosts = localhost, 127.0.0.1, ::1
```

→ `["localhost", "127.0.0.1", "::1"]`

### v4 compatibility alias

`get_value(section, option, default)` is preserved as a thin alias for
`get()`. Existing v4 code paths that get migrated to v5 do not need to be
rewritten on this front.

## Secret redaction — `as_dict_secure()`

Used by the unauthenticated REST API endpoints (`/api/5/config`,
`/api/5/args`) — CVE-2026-32609. It returns the same shape as `as_dict()`
but replaces values of secret-like options with `"***"`.

A key is considered secret if it contains (case-insensitive substring match)
any of:

```
password, passphrase, token, api_key, secret,
ssl_key, ssl_cert,
snmp_community, snmp_user, snmp_authkey, snmp_privkey,
uri
```

The match is intentionally permissive — over-redact rather than under-redact.

```python
config.as_dict()           # {"influxdb": {"password": "secret123"}}
config.as_dict_secure()    # {"influxdb": {"password": "***"}}
```

## Hot-reload

`reload()` re-runs the full layered overlay chain. It is currently a public
hook only — there is no automatic polling.

```python
config = GlancesConfigV5(cli_config_path="/path/to/conf")
# ... user edits the file ...
config.reload()   # picks up the changes
```

> **TODO Phase 4** — add an `mtime` polling task (every 5 s) that calls
> `reload()` for safe-to-reload keys (alert thresholds, display options).
> Credentials and `refresh_time` will require a process restart even after
> the polling lands.

## Adding a new default key

Add it to `GlancesConfigV5.DEFAULTS` in the same PR that introduces code
reading the key. Two rules:

1. **Every key read by the codebase must have a default** — either in
   `DEFAULTS`, or passed explicitly via `default=` to `get()`. Never rely on
   the value being present in some external config file.
2. **No silent type drift.** If a key starts as `int`, all callers must pass
   an `int` default. Mixing types across call sites breaks the type
   inference contract.

## Testing

Test stack: `unittest` + `unittest.mock` only (architecture decision §9, no
pytest).

The test file `tests/test_config_v5.py` provides a `_ConfigCase` base that
isolates each test in its own `tempfile.TemporaryDirectory` and patches:

- `os.environ` (cleared)
- `XDG_CONFIG_HOME` (pointed at the tmp dir)
- `HOME` (pointed at the tmp dir)
- `GlancesConfigV5.SYSTEM_CONFIG_PATH` (pointed at the tmp dir)

Use this base for any test that needs a controlled config environment.

## Module path

```
glances/config_v5.py        # implementation
tests/test_config_v5.py     # unit tests (42 tests, ~25 ms)
```

The v4 `glances/config.py` is **not modified**, **not imported**, **not
subclassed** by the v5 module. Strict isolation throughout the v5
transition.
