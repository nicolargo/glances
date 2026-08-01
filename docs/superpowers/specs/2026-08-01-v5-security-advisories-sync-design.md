# Design — Sync the v5 security plan with the v4 advisories fixed after 2026-06-20

Date: 2026-08-01
Branch: `develop-v5`
Status: approved

## 1. Problem

`docs/architecture/glances-v5-architecture-decisions.md` §8 is the source of
truth for "every published advisory against Glances v4 is reproduced or
resolved in v5.0". It was last synced on **2026-06-20** (v4.5.5 batch).

Five advisories were fixed on `develop` after that date and appear in
neither §8 nor its mirror `.claude/skills/SKILL-security.md`:

| Advisory | v4 commit | Date |
|---|---|---|
| GHSA-73wf-9vmv-5pv9 — incomplete fix of CVE-2026-32608 (nested stat values) | `ea4cf2f5` | 2026-06-28 |
| GHSA-59fj-m2j6-hcxh — incomplete fix of CVE-2026-53925 (on-alert action commands) | `5c07c0d9` | 2026-07-04 |
| GHSA-fp27-88fp-2phg — CORS credentials guard uses exact match | `89085894` | 2026-07-04 |
| GHSA-qcpp-8x79-hhp3 — incomplete fix of CVE-2026-32608 (cross-field operator reconstruction) | `9c280eae` | 2026-07-05 |
| CVE-2026-68520 / GHSA-4h34-v6r8-mmjc — `as_dict_secure()` value-level bypass | `8d0f8276` | 2026-08-01 |

Because the v5 REST/config/actions layers are rewrites (`config_v5.py`,
`webserver_v5.py`, `actions_v5/`), the v4 fixes do **not** reach v5 through
the weekly `develop → develop-v5` merge. Each one needs an explicit v5
verdict.

## 2. Assessment of the v5 code against each advisory

### 2.1 CVE-2026-68520 — v5 is vulnerable

`GlancesConfigV5.as_dict_secure()` (`glances/config_v5.py:293`) redacts on
the **option name** only:

```python
result[section] = {
    key: (self.SECRET_REDACTED if self._is_secret_key(key) else value)
    for key, value in options.items()
}
```

A credential embedded in a **value** survives. `/api/5/config` is reachable
unauthenticated by default, so:

```ini
[influxdb]
url = https://admin:s3cr3t@influx.example.com
```

is returned verbatim. `SECRET_KEYS` also lacks `username`, `user` and
`login`, which v4 added in the same commit.

### 2.2 GHSA-59fj-m2j6-hcxh — v5 has a gap

v4 gates the on-alert action command line behind `--disable-config-exec`:
`GlancesActions.allow_operators()` feeds `secure_popen(..., allow_operators=)`,
so a hardened deployment stops `secure_popen` from interpreting `&&`, `|`,
`>`, `>>` in a command line read from `glances.conf`.

v5 has no equivalent: `ShellAction.execute()` always calls
`asyncio.create_subprocess_shell()`, and `disable_config_exec` does not
exist anywhere under `glances/*_v5*` or `glances/actions_v5/`.

Decision: **port an equivalent gate** in the actions/amps cycle — when the
gate is on, config-sourced action commands execute through an explicit
argument list (`shell=False`), never a shell.

### 2.3 GHSA-73wf-9vmv-5pv9 and GHSA-qcpp-8x79-hhp3 — covered by a different mechanism

Both are bypasses of v4's *operator-stripping* sanitizer, which replaces
`&&`, `|`, `>`, `>>` (and now a lone `&`) by spaces in each Mustache value.
v5 does not use that mechanism at all: `ShellAction.execute()` pre-quotes
every context value with `shlex.quote(str(value))` before rendering.

- **Nested values** — a `cmdline` list is stringified by `str(value)` and
  quoted as one token, so an attacker-controlled argv element cannot reach
  the shell as an operator.
- **Cross-field reconstruction** — verified against the installed
  `chevron`: `{{{b}}}{{{c}}}` with `b = shlex.quote("foo&")` and
  `c = shlex.quote("&bar")` renders `'foo&''&bar'`, which the shell parses
  as the single literal word `foo&&bar`. No operator is reconstructible
  across a variable boundary.

Neither bypass class exists in v5. What is missing is a **regression test**
locking the property in — without it, a future change from `shlex.quote` to
an operator-stripping approach would silently reintroduce both.

### 2.4 GHSA-fp27-88fp-2phg — already correct, untested

`webserver_v5._wire_cors()` (`glances/webserver_v5.py:262`) already uses a
membership test:

```python
if any(o == "*" for o in origins) and allow_credentials:
```

A multi-origin allowlist containing `*` is therefore caught. The v4 bug
(`cors_origins == ["*"]`) does not exist in v5. No test covers the
multi-origin case; `test_cors_wildcard_with_credentials_downgrades` only
exercises `cors_origins="*"`.

## 3. Design

### 3.1 Fourth v5 status value

§8 currently offers three statuses: `Carry forward`, `Resolved by
architecture`, `New v5 mitigation`. Neither fits §2.3 — the component was
not removed and the feature was not dropped; v5 simply prevents the class
of bug by another route, while still owing a test.

Add a fourth value:

> `Covered by a different v5 mechanism` — the vulnerability class cannot
> occur in v5 because the v5 implementation uses a different technique than
> the v4 fix. A regression test locking the v5 property in is mandatory.

Applied to GHSA-73wf-9vmv-5pv9 and GHSA-qcpp-8x79-hhp3.

### 3.2 `glances/config_v5.py` — value-level redaction

Three surgical changes.

1. A module-level regex scrubbing the `userinfo` component of a URL:

   ```python
   _URL_CREDENTIALS_RE = re.compile(r"(?<=://)[^/?#@\s]+@")
   ```

   The lookbehind anchors on `://`, so only a real URL authority is
   touched; a value that merely contains an `@` is left alone.

2. A new exact-match secret set alongside the existing substring set:

   ```python
   SECRET_KEYS_EXACT: set[str] = {"user", "login"}
   ```

   `SECRET_KEYS` gains `username`. `user` and `login` **cannot** go into
   `SECRET_KEYS`: that set is matched as a substring, so `user` would
   redact the `user_careful` / `user_warning` CPU and load thresholds —
   a regression on `/api/5/config` for every user. Exact match on the
   lower-cased option name reproduces the intent of v4's `\buser\b`.

3. `as_dict_secure()` delegates to a new classmethod:

   ```python
   @classmethod
   def _secure_value(cls, key: str, value: Any) -> Any:
       if cls._is_secret_key(key):
           return cls.SECRET_REDACTED
       if not isinstance(value, str):
           return value
       return _URL_CREDENTIALS_RE.sub(f"{cls.SECRET_REDACTED}@", value)
   ```

   Non-`str` values (bool flags, ports, refresh rates) cannot carry a
   credential and pass through untouched — same reasoning as v4's
   `secure_option()`.

`_is_secret_key()` gains the exact-match branch. `re` is added to the
imports.

**Behaviour change:** a bare `[<section>] user = bob` is now redacted to
`***`. This matches v4 as of `8d0f8276` and is the intended hardening;
`tests/test_config_v5.py::test_preserves_non_secret` asserts the old
behaviour and is updated accordingly.

**Out of scope:** `/api/5/args` does not exist in v5 yet. §8 records the
constraint that the endpoint, when it lands, must run its payload through
the same function.

### 3.3 Regression tests

| File | Test | Locks in |
|---|---|---|
| `tests/test_config_v5.py` | URL userinfo redacted; URL without userinfo untouched; `user` / `login` / `username` redacted; `user_careful` preserved; non-`str` value untouched | CVE-2026-68520 |
| `tests/test_action_shell_v5.py` | a nested list context value reaches the shell as a single quoted token | GHSA-73wf-9vmv-5pv9 |
| `tests/test_action_shell_v5.py` | two adjacent triple-brace variables whose values end/start with `&` cannot form `&&` | GHSA-qcpp-8x79-hhp3 |
| `tests/test_webserver_v5.py` | `cors_origins="*,https://trusted.example"` with credentials on still downgrades and warns | GHSA-fp27-88fp-2phg |

### 3.4 Plan documents

`docs/architecture/glances-v5-architecture-decisions.md` §8:

- "Last synced" line → 2026-08-01, naming the five advisories.
- Fourth status value documented.
- Five rows appended to the table, keyed by GHSA where no CVE is assigned.

`.claude/skills/SKILL-security.md` mirrors the same five rows, the fourth
status, and gains:

- the `--disable-config-exec` equivalent in "What's deferred";
- the `/api/5/args` constraint in the "Sensitive endpoints" checklist;
- `secure_option`-style value redaction in the `as_dict_secure()` section.

## 4. Non-goals

- No change to `webserver_v5.py` — §2.4 shows the code is already correct.
- No change to `actions_v5/` — the gate of §2.2 belongs to the actions/amps
  cycle, not this one.
- No `NEWS.rst` entry (maintainer-owned, release time).
- No re-audit of the advisories already listed in §8.

## 5. Verification

1. `pytest tests/test_config_v5.py tests/test_action_shell_v5.py tests/test_webserver_v5.py` — green.
2. Full suite — no regression against the current baseline.
3. `make lint && make format`.
4. The four new regression tests fail when their fix is reverted
   (checked for the `config_v5` ones; the three others are pure
   characterisation tests over unchanged code and must pass as written).
