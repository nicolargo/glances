# Glances v5 — amps plugin port (G6C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `amps` plugin (Application Monitoring Processes) to the v5 asyncio architecture — a collection of user-configured AMPs, each loaded dynamically, each on its own `refresh` cadence, each executing external commands under a bounded, `--disable-config-exec`-aware runner.

**Architecture:** The v4 AMP script contract is **frozen** (`GlancesAmp`, synchronous `update(process_list)` + `set_result()`), so third-party AMPs keep working; v5 runs them through `asyncio.to_thread`. What is replaced is the *orchestrator*: a new `glances/amps_list_v5.py::AmpsListV5` loads AMP modules with `importlib.import_module("glances.amps.<name>")` (no `sys.path` mutation), keeps its registry as an **instance** attribute, pre-compiles each AMP's regex once, and per cycle sets each AMP's process count synchronously while offloading the actual `update()` to a thread — but only when that AMP's own `Timer` has fired **and** no previous run is still in flight. A thin `glances/plugins/amps/model_v5.py::PluginModel` (`IS_COLLECTION=True`, primary key `name`, `SCHEDULE_AT_GLOBAL_REFRESH=True`) projects the AMP objects into the store and computes a bespoke `_levels` from `count` vs `countmin`/`countmax`. A dedicated `render_curses_v5.py` mirrors v4 `msg_curse()` in the RIGHT sidebar, where `amps` is already registered — no orchestrator change.

Two **blocking prerequisites** land first. Task 1: `GlancesAmp.load_config()` — reused verbatim — calls `config.items(section)` and `config.get_float_value(section, option)`, neither of which exists on `GlancesConfigV5`; both raise `AttributeError` today. Task 2: the optional per-AMP `timeout` key needs `secure_popen` to be able to terminate a hung command, which it currently cannot.

**Tech Stack:** Python, `glances/amps/amp.py` (v4 contract, reused), `importlib`, asyncio (`to_thread`, `create_task`), `glances/secure.py`, `glances.processes.glances_processes` singleton, curses renderer v5, pytest + pytest-asyncio (auto mode)

## Global Constraints

- **Mirror v4**: read v4 `msg_curse()` (`glances/plugins/amps/__init__.py:98-135`) and `AmpsList.update()` (`glances/amps_list.py:87-121`) before writing the renderer/orchestrator; divergent "clean generic" behaviour is a regression.
- **The v4 AMP contract is frozen** — `GlancesAmp.update(process_list)` stays synchronous and third-party AMP scripts must keep working unmodified. The only change to `glances/amps/amp.py` is the **additive** `timeout()` accessor.
- **`glances/amps_list.py` (v4) and `glances/plugins/amps/__init__.py` (v4) are NOT modified.** The v4 runtime on `develop` must be unaffected.
- **`glances/plugins/plugin/base_v5.py` is NOT modified** — same review criterion as G6B.
- **`glances/outputs/curses_renderer_v5.py` is NOT modified** — `amps` is already in `RIGHT_SLOT` (lines 75-83).
- **Every change to a shared v4 file is additive with an unchanged default**: `secure_popen(..., timeout=None)` and `GlancesAmp.timeout()` returning `None` when the key is absent must leave v4 behaviour bit-for-bit identical.
- **`get_float_value` must raise `ValueError` on a non-numeric value**, never fall back to the default — `load_config` depends on that exception to route string/list values. See finding #1.
- **Empty registry must stay valid**: no `[amp_*]` section, or every AMP disabled → empty payload, no TUI block, no crash.
- **Alerts fire on `warning`+ only**; `careful` is colour-only. `amps` sets `EMITS_ALERTS = False` — levels colour the TUI and never reach history or actions (v4 parity).
- **Plugin titles and column headers are ALWAYS `ColorRole.HEADER`** — never escalate from `_levels`. (`amps` has no title and no column header at all — v4 parity, see Task 6.)
- **The restricted `secure_popen` grammar is preserved** — `&&`, `|`, `>` only, no real shell. Do **not** align on `ShellAction`'s `create_subprocess_shell`; that would make `;`, `$()` and backticks interpretable where v4 does not interpret them.
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only (`git add`), never `git commit`.
- Tests: `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` + `.venv/bin/python -m ruff format`.

Design reference: `docs/superpowers/specs/2026-08-02-glances-v5-g6c-amps-design.md`.

---

## Key implementation findings (decided, not open)

1. **`GlancesConfigV5` is missing `items()` and `get_float_value()` — blocking, and `get_float_value` has a semantic trap.** `GlancesAmp.load_config()` (`glances/amps/amp.py:75-84`) does:

   ```python
   for param, _ in config.items(amp_section):
       try:
           self.configs[param] = config.get_float_value(amp_section, param)
       except ValueError:
           self.configs[param] = config.get_value(amp_section, param).split(',')
   ```

   `GlancesConfigV5` implements neither method (confirmed by grep: only `get`, `get_value`, `has_section`, `sections`, `section_keys`, `as_dict`, `as_dict_secure`, `reload`). v4's `get_float_value` (`glances/config.py:398`) delegates to `ConfigParser.getfloat`, which returns the default only on `NoOptionError`/`NoSectionError` and **raises `ValueError` on a present-but-non-numeric value** — that exception is load-bearing: it is what routes `regex=`, `command=`, `enable=` and `one_line=` to the string/list branch. A v5 implementation that swallowed it would turn every one of those into `0.0` and silently break every AMP. Same family as the G6B `get_value` fix: fix once in the config layer, never as a per-plugin shim. `get_int_value` / `get_bool_value` are **not** added — no v5 caller, and speculative API is dead code.

2. **v4's `AmpsList.__amps_dict` is a CLASS attribute.** `glances/amps_list.py:31` declares `__amps_dict = {}` at class scope and `load_configs` only ever does `self.__amps_dict[amp_name] = ...` — so every `AmpsList` instance shares one dict for the process lifetime. Invisible in production (one instance per run), fatal for test isolation and for any future config reload. `AmpsListV5` uses an **instance** attribute. This is a deliberate divergence, not an oversight.

3. **v4 `_build_amps_list` can raise `UnboundLocalError`.** `glances/amps_list.py:123-140` assigns `ret` inside a `try` that catches `(TypeError, KeyError)`, then returns `ret` unconditionally — so any process dict missing `pid`/`cpu_percent`/`memory_percent` turns a caught `KeyError` into an uncaught `UnboundLocalError` one line later. `AmpsListV5._match()` returns `[]` on that path, and Task 4 covers it with a regression test.

4. **The in-flight check must come BEFORE `should_update()`.** `GlancesAmp.should_update()` (`glances/amps/amp.py:149-160`) has a **side effect**: when the timer has finished it re-arms and resets it, then returns `enable()`. Calling it and *then* discovering a run is already in flight would consume that timer tick and silently double the AMP's effective period. Order is: `if name in self._inflight: return` → `if not amp.should_update(): return` → launch.

5. **`ModuleNotFoundError` has two distinct meanings at load time.** `import_module("glances.amps.foo")` raises it both when there is no dedicated `foo` AMP (→ fall back to `glances.amps.default`, which is the documented behaviour for every `command=`-based AMP) and when the AMP module itself imports a missing third-party library (→ v4 logs `"Missing Python Lib (…), cannot load AMP …"` and skips the AMP entirely). Discriminate on `e.name == module_name`: equal means the AMP module itself is absent, anything else means one of its dependencies is.

6. **The AMP display name is `Amp.NAME`, not the config section suffix.** v4's plugin stores `'name': v.NAME` (`glances/plugins/amps/__init__.py:60`), and `glances/amps/default/__init__.py:43` sets `self.NAME = name.capitalize()`. So `[amp_dropbox]` displays and keys as `Dropbox`, while the *registry* key and the module name stay lowercase `dropbox`. Keep both — the primary key is `NAME` (v4 parity for the API payload), the registry key is the section suffix.

7. **`asyncio.to_thread` is not cancellable, and no `stop()` override is added.** A hung AMP keeps its thread; as in v4 those threads are not daemons, so interpreter shutdown waits for them. The in-flight guard bounds the leak to one thread per AMP rather than one per cycle, which is the operational regression that matters. Adding a `stop()` that calls `task.cancel()` would be **worse than nothing**: `AsyncScheduler.stop()` invokes `plugin.stop()` via `asyncio.to_thread` (`glances/scheduler_v5.py:188`), so those `cancel()` calls would happen off the event loop thread, which is not thread-safe. No `stop()` override — deliberate, documented in design §9.

8. **`SCHEDULE_AT_GLOBAL_REFRESH = True` is required, and `[amps] refresh` is meaningless.** Each AMP owns its cadence through its own `Timer`; the plugin's job is to publish the current results promptly. Registering `amps` at a per-plugin `refresh` would throttle publication of results the AMPs already produced — the exact bug `ports` fixed with this flag (`glances/plugins/plugin/base_v5.py:95-109`). There is no `[amps]` section in the shipped `conf/glances.conf` and none is added.

9. **`systemd`'s `except` tuple must grow `TimeoutExpired`.** `glances/amps/systemd/__init__.py:63` catches `(OSError, CalledProcessError)`. Once `check_output(..., timeout=…)` can raise `subprocess.TimeoutExpired` — a `SubprocessError`, sibling of `CalledProcessError`, not a subclass — an unconfigured except tuple would let it escape into the worker thread and be swallowed as a generic task exception with no useful message.

---

## File Structure

```
glances/config_v5.py                  (MODIFIED — items() + get_float_value())
glances/secure.py                     (MODIFIED — secure_popen(..., timeout=None))
glances/amps/amp.py                   (MODIFIED — additive timeout() accessor)
glances/amps/default/__init__.py      (MODIFIED — forward timeout to secure_popen)
glances/amps/systemv/__init__.py      (MODIFIED — forward timeout to secure_popen)
glances/amps/systemd/__init__.py      (MODIFIED — forward timeout to check_output + TimeoutExpired)
glances/amps/nginx/__init__.py        (MODIFIED — self.timeout() or 15)
glances/amps_list_v5.py               (NEW — AmpsListV5: loader, cadence, bounded runner)
glances/amps_list.py                  (v4 — untouched)
glances/plugins/amps/
  __init__.py                         (v4 — untouched; kept for the v4 runtime)
  model_v5.py                         (NEW — PluginModel: projection + bespoke _derived_parameters)
  render_curses_v5.py                 (NEW — name / count / result rows, no title)
tests/
  test_config_v5.py                   (MODIFIED — items() + get_float_value())
  test_amp_secure_popen.py            (MODIFIED — timeout parameter)
  test_amps_list_v5.py                (NEW — loader, cadence, in-flight guard, branches)
  test_plugin_amps_v5.py              (NEW — identity, projection, level ladder, empty)
  test_plugin_amps_render_curses_v5.py (NEW — 3-column layout, multi-line, colour)
conf/glances.conf                     (MODIFIED — document the optional `timeout` key)
docs/aoa/amps.rst                     (MODIFIED — document the optional `timeout` key)
docs/architecture/glances-v5-architecture-decisions.md (MODIFIED — close the two AMP CVE carry-forwards)
```

---

## Task 1: `GlancesConfigV5.items()` and `get_float_value()`

**Files:**
- Modify: `glances/config_v5.py` (after `get_value`, around line 273; and next to `section_keys`, around line 301)
- Test: `tests/test_config_v5.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `GlancesConfigV5.items(section: str) -> list[tuple[str, Any]]` and `GlancesConfigV5.get_float_value(section: str, option: str, default: float = 0.0) -> float`. Task 3 relies on both being callable by the verbatim `GlancesAmp.load_config()`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config_v5.py` (the `env` fixture, `write()` and `xdg_path()` helpers already exist at the top of that file):

```python
# ============================================================================
# v4-compatibility accessors used by verbatim-reused v4 code (GlancesAmp)
# ============================================================================


def test_items_returns_section_pairs(env: Path) -> None:
    write(xdg_path(env), "[amp_foo]\nenable = true\nrefresh = 3\n")
    items = dict(GlancesConfigV5().items("amp_foo"))
    assert items == {"enable": "true", "refresh": "3"}


def test_items_missing_section_returns_empty_list(env: Path) -> None:
    assert GlancesConfigV5().items("amp_does_not_exist") == []


def test_get_float_value_reads_a_number(env: Path) -> None:
    write(xdg_path(env), "[amp_foo]\nrefresh = 3\n")
    assert GlancesConfigV5().get_float_value("amp_foo", "refresh") == 3.0


def test_get_float_value_missing_option_returns_default(env: Path) -> None:
    write(xdg_path(env), "[amp_foo]\nrefresh = 3\n")
    assert GlancesConfigV5().get_float_value("amp_foo", "countmin", 7) == 7.0


def test_get_float_value_missing_section_returns_default(env: Path) -> None:
    assert GlancesConfigV5().get_float_value("nope", "nope", 1.5) == 1.5


def test_get_float_value_raises_on_non_numeric_value(env: Path) -> None:
    """Load-bearing: GlancesAmp.load_config() routes every string and
    comma-list config value through the `except ValueError` branch. If this
    returned the default instead of raising, `regex=`, `command=` and
    `enable=` would all silently become 0.0 and every AMP would break."""
    write(xdg_path(env), "[amp_foo]\nregex = .*python.*\n")
    with pytest.raises(ValueError):
        GlancesConfigV5().get_float_value("amp_foo", "regex")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config_v5.py -k "items or get_float_value" -v`
Expected: FAIL — `AttributeError: 'GlancesConfigV5' object has no attribute 'items'` / `... 'get_float_value'`

- [ ] **Step 3: Implement `get_float_value`**

In `glances/config_v5.py`, immediately after the `get_value` method (which ends with `return self.get(section, option, default)`), add:

```python
    def get_float_value(self, section: str, option: str, default: float = 0.0) -> float:
        """v4 compatibility accessor — mirrors `GlancesConfig.get_float_value`.

        Returns `float(default)` when the option is ABSENT, and `float(raw)`
        when it is present. A present-but-non-numeric value therefore raises
        `ValueError`, exactly like v4's `ConfigParser.getfloat`.

        That exception is load-bearing, not incidental:
        `GlancesAmp.load_config()` (reused verbatim from v4) calls this method
        on EVERY key of an `[amp_*]` section and relies on `ValueError` to
        route the string and comma-list values (`regex`, `command`, `enable`,
        `one_line`, …) to its fallback branch. Swallowing it and returning the
        default would coerce all of them to 0.0 and silently break every AMP.
        """
        raw = self._merged.get(section, {}).get(option)
        if raw is None:
            return float(default)
        return float(raw)
```

- [ ] **Step 4: Implement `items`**

In `glances/config_v5.py`, in the "introspect" block, immediately after `section_keys`, add:

```python
    def items(self, section: str) -> list[tuple[str, Any]]:
        """Return the `(option, value)` pairs of `section` (empty if absent).

        v4 compatibility accessor: `GlancesAmp.load_config()` iterates
        `config.items(amp_section)` to discover an AMP's keys, which are
        arbitrary (`status_url`, `systemctl_cmd`, any user-defined option)
        and therefore cannot be enumerated statically.
        """
        return list(self._merged.get(section, {}).items())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_config_v5.py -v`
Expected: PASS (the whole file, not just the new tests — the additions must not disturb the existing loader tests)

- [ ] **Step 6: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/config_v5.py tests/test_config_v5.py
.venv/bin/python -m ruff format glances/config_v5.py tests/test_config_v5.py
git add glances/config_v5.py tests/test_config_v5.py
```

---

## Task 2: bounded command execution — `secure_popen(timeout=)` and `GlancesAmp.timeout()`

**Files:**
- Modify: `glances/secure.py:17-64` (`secure_popen`, `__run_argv`, `__secure_popen`)
- Modify: `glances/amps/amp.py` (add `timeout()` next to `refresh()`, around line 137)
- Modify: `glances/amps/default/__init__.py:69`, `glances/amps/systemv/__init__.py:60`, `glances/amps/systemd/__init__.py:57-64`, `glances/amps/nginx/__init__.py:69`
- Modify: `conf/glances.conf` (AMPS header comment block, around line 1041)
- Modify: `docs/aoa/amps.rst` ("Security considerations" section)
- Test: `tests/test_amp_secure_popen.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `secure_popen(cmd: str, allow_operators: bool = True, timeout: float | None = None) -> str` and `GlancesAmp.timeout() -> float | None`. Task 4 relies on the AMPs honouring the `timeout` config key without any further plumbing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_amp_secure_popen.py`:

```python
# ---------------------------------------------------------------------------
# secure_popen(timeout=...)
# ---------------------------------------------------------------------------


def test_timeout_none_is_the_default_and_changes_nothing():
    """Default behaviour must be bit-for-bit v4: no timeout at all."""
    assert secure_popen('echo hello').strip() == 'hello'
    assert secure_popen('echo hello', timeout=None).strip() == 'hello'


def test_timeout_not_reached_returns_the_output():
    assert secure_popen('echo hello', timeout=10).strip() == 'hello'


def test_timeout_kills_a_hanging_command():
    start = time.monotonic()
    ret = secure_popen('sleep 30', timeout=0.5)
    elapsed = time.monotonic() - start
    assert 'timeout' in ret.lower()
    assert elapsed < 10, 'the command was not killed'


def test_timeout_applies_without_operators():
    start = time.monotonic()
    ret = secure_popen('sleep 30', allow_operators=False, timeout=0.5)
    elapsed = time.monotonic() - start
    assert 'timeout' in ret.lower()
    assert elapsed < 10, 'the command was not killed'


def test_amp_timeout_accessor_defaults_to_none():
    amp = _make_amp('echo hello', disable_config_exec=False)
    assert amp.timeout() is None


def test_amp_timeout_accessor_reads_the_config_key():
    amp = _make_amp('echo hello', disable_config_exec=False)
    amp.configs['timeout'] = 2.0
    assert amp.timeout() == 2.0
```

Add `import time` to that file's imports.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_amp_secure_popen.py -k "timeout" -v`
Expected: FAIL — `TypeError: secure_popen() got an unexpected keyword argument 'timeout'`

- [ ] **Step 3: Thread `timeout` through `glances/secure.py`**

Replace the body of `glances/secure.py` from the import line down to the end with:

```python
import re
from subprocess import PIPE, Popen, TimeoutExpired

from glances.globals import nativestr


def secure_popen(cmd, allow_operators=True, timeout=None):
    """A more or less secure way to execute system commands.

    By default the following shell-like operators are interpreted:
    - '&&' to chain commands
    - '|'  to pipe a command output into the next one
    - '>'  to redirect the output to a file

    :param cmd: the command line to run (str)
    :param allow_operators: when False, the operators above are NOT
        interpreted but passed verbatim as literal arguments. The command is
        then run as a single process that can neither chain, pipe nor write to
        an arbitrary file. Used for commands coming from the configuration file
        when --disable-config-exec is set (GHSA-3vwc-qwhc-3mj7).
    :param timeout: when set, kill the command after `timeout` seconds and
        return an error string instead of its output. `None` (the default)
        means no timeout at all — the historical behaviour, unchanged. With
        '&&'-chained commands the timeout applies to EACH sub-command, not to
        the chain as a whole.

    :return: the result of the command(s) (str)
    """
    if not allow_operators:
        # Run the whole command as a single process: '&&', '|' and '>' are
        # passed verbatim as arguments and never interpreted.
        return __run_argv(cmd, timeout=timeout)

    ret = ''

    # Split by multiple commands (only '&&' separator is supported)
    for c in cmd.split('&&'):
        ret += __secure_popen(c, timeout=timeout)

    return ret


def __split_args(cmd):
    """Split a command string into an argument list.

    Spaces are the separators, except within single or double quotes (the
    surrounding quotes are then removed).
    """
    tmp_split = [_ for _ in list(filter(None, re.split(r'(\s+)|(".*?"+?)|(\'.*?\'+?)', cmd))) if _ != ' ']
    return [_[1:-1] if (_[0] == _[-1] == '"') or (_[0] == _[-1] == '\'') else _ for _ in tmp_split]


def __communicate(p_list, timeout):
    """Wait for the pipeline to finish, killing it if `timeout` expires.

    Returns the (stdout, stderr) tuple, or None when the timeout fired (the
    caller then reports the error string).
    """
    try:
        return p_list[-1].communicate(timeout=timeout)
    except TimeoutExpired:
        for p in p_list:
            p.kill()
        # Reap the killed processes so no zombie is left behind.
        for p in p_list:
            p.wait()
        return None


def __run_argv(cmd, timeout=None):
    """Execute cmd as a single process, without interpreting any operator."""
    p = Popen(__split_args(cmd), shell=False, stdin=None, stdout=PIPE, stderr=PIPE)
    p_ret = __communicate([p], timeout)
    if p_ret is None:
        return f'Glances error: command timeout after {timeout}s ({cmd})'
    if nativestr(p_ret[1]) == '':
        return nativestr(p_ret[0])
    return nativestr(p_ret[1])


def __secure_popen(cmd, timeout=None):
    """A more or less secure way to execute system command

    Manage redirection (>) and pipes (|)
    """
    # Split by redirection '>'
    cmd_split_redirect = cmd.split('>')
    if len(cmd_split_redirect) > 2:
        return f'Glances error: Only one file redirection allowed ({cmd})'
    if len(cmd_split_redirect) == 2:
        stdout_redirect = cmd_split_redirect[1].strip()
        cmd = cmd_split_redirect[0]
    else:
        stdout_redirect = None

    sub_cmd_stdin = None
    p_list = []
    # Split by pipe '|'
    for sub_cmd in cmd.split('|'):
        # Split by space character, but do no split spaces within quotes (remove surrounding quotes, though)
        sub_cmd_split = __split_args(sub_cmd)
        p = Popen(sub_cmd_split, shell=False, stdin=sub_cmd_stdin, stdout=PIPE, stderr=PIPE)
        if p_list:
            # Allow the previous process to receive a SIGPIPE if p exits.
            p_list[-1].stdout.close()
        p_list.append(p)
        sub_cmd_stdin = p.stdout

    p_ret = __communicate(p_list, timeout)
    if p_ret is None:
        return f'Glances error: command timeout after {timeout}s ({cmd})'
    # Reap the upstream processes of the pipeline (they exited on their own)
    for p in p_list[:-1]:
        p.wait()

    if nativestr(p_ret[1]) == '':
        # No error
        ret = nativestr(p_ret[0])
        if stdout_redirect is not None:
            # Write result to redirection file
            with open(stdout_redirect, "w") as stdout_redirect_file:
                stdout_redirect_file.write(ret)
    else:
        # Error
        ret = nativestr(p_ret[1])

    return ret
```

- [ ] **Step 4: Add the `timeout()` accessor to `GlancesAmp`**

In `glances/amps/amp.py`, immediately after the `refresh()` method, add:

```python
    def timeout(self):
        """Return the optional command timeout in seconds, or None.

        Optional `timeout=N` key of the `[amp_<name>]` section. `None` — the
        default when the key is absent — means no timeout at all, which is the
        historical v4 behaviour and stays the shipped default.
        """
        return self.get('timeout')
```

- [ ] **Step 5: Forward the timeout in the four embedded AMPs**

`glances/amps/default/__init__.py` — replace the `secure_popen` call:

```python
            self.set_result(
                secure_popen(res, allow_operators=self.allow_operators(), timeout=self.timeout()).rstrip()
            )
```

`glances/amps/systemv/__init__.py` — replace the `secure_popen` call:

```python
            res = secure_popen(self.get('service_cmd'), allow_operators=self.allow_operators(), timeout=self.timeout())
```

`glances/amps/systemd/__init__.py` — replace the import, the call and the `except` tuple:

```python
from subprocess import CalledProcessError, TimeoutExpired, check_output
```

```python
        try:
            res = check_output(self.get('systemctl_cmd').split(), timeout=self.timeout())
        except (OSError, CalledProcessError, TimeoutExpired) as e:
            logger.debug(f'{self.NAME}: Error while executing systemctl ({e})')
```

`TimeoutExpired` is a `SubprocessError`, **not** a subclass of `CalledProcessError` — without adding it here the exception escapes into the worker thread.

`glances/amps/nginx/__init__.py` — replace the hardcoded timeout:

```python
        res = requests.get(self.get('status_url'), timeout=self.timeout() or 15)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_amp_secure_popen.py -v`
Expected: PASS — including the pre-existing GHSA-3vwc-qwhc-3mj7 regression tests, which must be unaffected.

- [ ] **Step 7: Document the `timeout` key**

In `conf/glances.conf`, inside the `# AMPS` header comment block, add one line after the `refresh` line:

```
# * timeout: (optional) kill the AMP command after timeout seconds
#            Default: no timeout, the command runs to completion
```

No `timeout=` key is added to any shipped `[amp_*]` section — the default stays v4's.

In `docs/aoa/amps.rst`, at the end of the "Security considerations" section, add:

```rst
An AMP command that hangs blocks that AMP indefinitely. The optional
``timeout`` key bounds it:

.. code-block:: ini

    [amp_dropbox]
    enable=true
    regex=.*dropbox.*
    refresh=3
    command=dropbox status
    timeout=10

Without the key there is no timeout, which is the historical behaviour. Note
that with ``&&``-chained commands the timeout applies to each sub-command, not
to the chain as a whole.
```

- [ ] **Step 8: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/secure.py glances/amps/ tests/test_amp_secure_popen.py
.venv/bin/python -m ruff format glances/secure.py glances/amps/ tests/test_amp_secure_popen.py
git add glances/secure.py glances/amps/ conf/glances.conf docs/aoa/amps.rst tests/test_amp_secure_popen.py
```

---

## Task 3: `AmpsListV5` — loader

**Files:**
- Create: `glances/amps_list_v5.py`
- Test: `tests/test_amps_list_v5.py`

**Interfaces:**
- Consumes: `GlancesConfigV5.items()` and `get_float_value()` from Task 1 (via the verbatim `GlancesAmp.load_config`); `GlancesAmp.timeout()` from Task 2.
- Produces: `AmpsListV5(config: GlancesConfigV5)` with `self._amps: dict[str, GlancesAmp]` (registry keyed by config-section suffix) and `self._regex: dict[str, re.Pattern[str]]`. Task 4 adds `async def update()` to this same class; Task 5 constructs it from the plugin.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_amps_list_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for AmpsListV5 (loader half; cadence in Task 4)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from glances.amps_list_v5 import AmpsListV5
from glances.config_v5 import GlancesConfigV5


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a GlancesConfigV5 from an inline config body."""

    def _make(body: str) -> GlancesConfigV5:
        xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
        xdg_conf.parent.mkdir(parents=True, exist_ok=True)
        xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
        monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        return GlancesConfigV5()

    return _make


def test_no_amp_section_yields_an_empty_registry(cfg):
    amps = AmpsListV5(cfg("[global]\nrefresh = 2\n"))
    assert amps._amps == {}


def test_unknown_amp_falls_back_to_the_default_module(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            command=echo hello
            """
        )
    )
    assert "foo" in amps._amps
    assert type(amps._amps["foo"]).__module__ == "glances.amps.default"
    # default AMP capitalises the name (v4 parity)
    assert amps._amps["foo"].NAME == "Foo"


def test_named_module_is_loaded_when_it_exists(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_systemd]
            enable=true
            regex=systemd
            refresh=30
            systemctl_cmd=/bin/systemctl --plain
            """
        )
    )
    assert type(amps._amps["systemd"]).__module__ == "glances.amps.systemd"


def test_amp_module_with_a_missing_dependency_is_skipped(monkeypatch, cfg):
    """`ModuleNotFoundError` means two different things (finding #5): no
    dedicated AMP module (-> fall back to `default`) versus the AMP module
    existing but importing a missing third-party lib (-> skip the AMP, as v4
    does with its "Missing Python Lib" warning). Discriminated on `e.name`."""
    import importlib as _importlib

    real_import = _importlib.import_module

    def _fake_import(name, *args, **kwargs):
        if name == "glances.amps.nginx":
            raise ModuleNotFoundError("No module named 'requests'", name="requests")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("glances.amps_list_v5.importlib.import_module", _fake_import)

    amps = AmpsListV5(cfg("[amp_nginx]\nenable=true\nregex=nginx\nrefresh=60\n"))
    assert amps._amps == {}, "the AMP must be skipped, not silently replaced by the default one"


def test_config_is_loaded_into_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            countmin=1
            command=echo hello
            """
        )
    )
    amp = amps._amps["foo"]
    assert amp.enable() is True
    assert amp.refresh() == 3.0
    assert amp.count_min() == 1.0
    assert amp.regex() == ".*foo.*"


def test_invalid_amp_name_falls_back_to_the_default_module(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_not-an-identifier]
            enable=true
            refresh=3
            command=echo hello
            """
        )
    )
    assert type(amps._amps["not-an-identifier"]).__module__ == "glances.amps.default"


def test_regex_is_precompiled_once(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            """
        )
    )
    assert amps._regex["foo"].pattern == ".*foo.*"


def test_regexless_amp_has_no_compiled_pattern(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_conntrack]
            enable=true
            refresh=30
            command=echo hello
            """
        )
    )
    assert "conntrack" in amps._amps
    assert "conntrack" not in amps._regex


def test_invalid_regex_disables_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=(unclosed
            refresh=3
            """
        )
    )
    assert amps._amps["foo"].enable() is False


def test_registry_is_per_instance_not_shared(cfg):
    """v4's AmpsList.__amps_dict is a CLASS attribute shared by every
    instance (glances/amps_list.py:31). AmpsListV5 must not repeat that."""
    a = AmpsListV5(cfg("[amp_foo]\nenable=true\nrefresh=3\ncommand=echo a\n"))
    b = AmpsListV5(cfg("[global]\nrefresh = 2\n"))
    assert list(a._amps) == ["foo"]
    assert b._amps == {}


def test_disable_config_exec_reaches_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [global]
            disable_config_exec=true

            [amp_foo]
            enable=true
            refresh=3
            command=echo hello
            """
        )
    )
    assert amps._amps["foo"].allow_operators() is False


def test_disable_config_exec_defaults_to_allowing_operators(cfg):
    amps = AmpsListV5(cfg("[amp_foo]\nenable=true\nrefresh=3\ncommand=echo hello\n"))
    assert amps._amps["foo"].allow_operators() is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_amps_list_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.amps_list_v5'`

- [ ] **Step 3: Implement the loader**

Create `glances/amps_list_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — AMP orchestrator.

Replaces v4's `glances/amps_list.py::AmpsList` (left untouched for the v4
runtime). The AMP-facing contract is unchanged — an AMP is still a
`GlancesAmp` subclass with a synchronous `update(process_list)` — so
third-party AMP scripts written for v4 keep working. What changes is the
orchestration around them:

- **Loading**: `importlib.import_module("glances.amps.<name>")` instead of
  `__import__` on a bare basename with `glances/amps/` injected into
  `sys.path`. No global import-path mutation, so an AMP named after a stdlib
  module (`[amp_email]`) no longer shadows it process-wide.
- **Registry**: an INSTANCE attribute. v4 keeps it on the class, so every
  `AmpsList` shares one dict for the process lifetime.
- **Matching**: each AMP's regex is compiled ONCE at load time instead of
  being re-parsed for every process on every cycle.
- **Execution**: `asyncio.to_thread`, launched only when the AMP's own
  `Timer` has fired AND no previous run is still in flight — v4 spawns an
  un-joined thread per AMP per cycle unconditionally, so a hung command
  leaks one thread every `refresh` seconds forever.

See docs/superpowers/specs/2026-08-02-glances-v5-g6c-amps-design.md.
"""

from __future__ import annotations

import importlib
import logging
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from glances.amps.amp import GlancesAmp
    from glances.config_v5 import GlancesConfigV5

logger = logging.getLogger(__name__)

_SECTION_PREFIX = "amp_"
_DEFAULT_MODULE = "glances.amps.default"


class AmpsListV5:
    """Load, schedule and run the configured AMPs."""

    def __init__(self, config: GlancesConfigV5) -> None:
        self.config = config

        # `GlancesAmp.allow_operators()` reads `args.disable_config_exec`, and
        # v5 hands plugins a config object, not an argparse namespace. Build the
        # minimal shim the frozen v4 contract expects. `main_v5` already
        # overlays this key onto `[global]` when `--disable-config-exec` is
        # passed (main_v5.py:386-392).
        self._args = SimpleNamespace(
            disable_config_exec=bool(config.get("global", "disable_config_exec", False)),
        )

        # INSTANCE attributes, all keyed by the config-section suffix
        # (`[amp_foo]` -> "foo"), which is NOT the display name (`Amp.NAME`).
        self._amps: dict[str, GlancesAmp] = {}
        self._regex: dict[str, re.Pattern[str]] = {}

        self._load()

    # ------------------------------------------------------------- loading

    def _load(self) -> None:
        for section in self.config.sections():
            if not section.startswith(_SECTION_PREFIX):
                continue
            name = section[len(_SECTION_PREFIX) :]
            amp = self._instantiate(name)
            if amp is None:
                continue
            amp.load_config(self.config)
            self._amps[name] = amp
            self._compile_regex(name, amp)
        logger.debug("AMPs list: %s", list(self._amps))

    def _instantiate(self, name: str) -> GlancesAmp | None:
        """Import the AMP module for `name` and build its `Amp` instance.

        Falls back to the `default` AMP when no dedicated module exists —
        the documented behaviour for every `command=`-based AMP.
        """
        module = self._import_amp_module(name)
        if module is None:
            return None
        try:
            return module.Amp(name=name, args=self._args)
        except Exception as e:
            logger.warning("Cannot build AMP %s (%s)", name, e)
            return None

    def _import_amp_module(self, name: str) -> Any | None:
        """Return the module backing AMP `name`, or None to skip it entirely.

        A name that is not a valid Python identifier can never be a module,
        so it goes straight to the default AMP instead of producing a
        confusing import error.
        """
        module_name = f"glances.amps.{name}" if name.isidentifier() else None

        if module_name is not None:
            try:
                return importlib.import_module(module_name)
            except ModuleNotFoundError as e:
                if e.name != module_name:
                    # The AMP module exists but one of ITS imports is missing.
                    # v4 logs "Missing Python Lib" and skips the AMP — do not
                    # silently substitute the default AMP for it.
                    logger.warning("Missing Python lib (%s), cannot load AMP %s", e, name)
                    return None
                # No dedicated module for this AMP — fall through to default.
            except Exception as e:
                logger.warning("Cannot load AMP %s (%s)", name, e)
                return None

        try:
            return importlib.import_module(_DEFAULT_MODULE)
        except Exception as e:  # pragma: no cover — the default AMP ships with Glances
            logger.warning("Cannot load the default AMP module (%s)", e)
            return None

    def _compile_regex(self, name: str, amp: GlancesAmp) -> None:
        """Compile the AMP's regex once. No regex is a valid case (issue #1690).

        An invalid regex disables the AMP, mirroring how `load_config`
        disables an AMP that lacks the mandatory `refresh` key.
        """
        pattern = amp.regex()
        if pattern is None:
            return
        try:
            self._regex[name] = re.compile(pattern)
        except re.error as e:
            logger.warning("AMP %s: invalid regex %r (%s) — the AMP is disabled", name, pattern, e)
            amp.configs["enable"] = "false"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_amps_list_v5.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/amps_list_v5.py tests/test_amps_list_v5.py
.venv/bin/python -m ruff format glances/amps_list_v5.py tests/test_amps_list_v5.py
git add glances/amps_list_v5.py tests/test_amps_list_v5.py
```

---

## Task 4: `AmpsListV5` — update cycle, cadence and in-flight guard

**Files:**
- Modify: `glances/amps_list_v5.py` (append the update half to the class)
- Test: `tests/test_amps_list_v5.py`

**Interfaces:**
- Consumes: `AmpsListV5._amps` / `._regex` from Task 3.
- Produces: `async def update(self) -> list[GlancesAmp]` — returns every loaded AMP (enabled or not), in load order, with `count`/`result` up to date. Task 5's `_grab_stats()` consumes exactly this.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_amps_list_v5.py` (add `import asyncio`, `import threading`, and `from glances import amps_list_v5 as amps_module` to the imports):

```python
# ---------------------------------------------------------------------------
# update cycle
# ---------------------------------------------------------------------------

_PROC_PYTHON = {"pid": 11, "name": "python3", "cmdline": ["python3", "app.py"], "cpu_percent": 1.0, "memory_percent": 2.0}
_PROC_NGINX = {"pid": 22, "name": "nginx", "cmdline": ["/usr/sbin/nginx"], "cpu_percent": 3.0, "memory_percent": 4.0}


@pytest.fixture
def procs(monkeypatch):
    """Control the process list the AMPs match against."""

    def _set(processlist):
        monkeypatch.setattr(
            amps_module.glances_processes,
            "get_list",
            lambda: list(processlist),
            raising=False,
        )

    return _set


async def _settle(amps: AmpsListV5) -> None:
    """Await every in-flight AMP run."""
    while amps._inflight:
        await asyncio.gather(*list(amps._inflight.values()), return_exceptions=True)
        await asyncio.sleep(0)


async def test_count_reflects_the_matching_processes(cfg, procs):
    procs([_PROC_PYTHON, _PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1


async def test_cmdline_is_searched_too(cfg, procs):
    procs([{"pid": 1, "name": "sh", "cmdline": ["/usr/bin/foo", "--daemon"], "cpu_percent": 0.0, "memory_percent": 0.0}])
    amps = AmpsListV5(cfg("[amp_foo]\nenable=true\nregex=.*foo.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["foo"].count() == 1


async def test_disabled_amp_is_never_run(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=false\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_regexless_amp_runs_with_an_empty_process_list(cfg, procs):
    """Issue #1690 — no regex means 'run every refresh seconds'."""
    procs([])
    amps = AmpsListV5(cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["conntrack"].count() == 0
    assert amps._amps["conntrack"].result().strip() == "tracked"


async def test_no_match_sets_the_no_running_process_message(cfg, procs):
    procs([_PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncountmin=1\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 0
    assert amps._amps["python"].result() == "No running process"


async def test_no_match_without_countmin_leaves_the_result_alone(cfg, procs):
    procs([_PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_no_match_does_not_run_the_command(cfg, procs):
    """v4 does not call update() on the no-match branch — nor do we."""
    procs([_PROC_NGINX])
    amps = AmpsListV5(
        cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncommand=echo ran\n")
    )
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_count_is_refreshed_even_when_the_timer_has_not_fired(cfg, procs):
    """The count must track the process list on EVERY cycle; only the
    (possibly expensive) update() is gated by the AMP's own refresh."""
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3600\ncommand=echo ran\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1

    calls = []
    amps._amps["python"].update = lambda process_list: calls.append(process_list)
    procs([_PROC_PYTHON, dict(_PROC_PYTHON, pid=12)])
    await amps.update()
    await _settle(amps)

    assert amps._amps["python"].count() == 2, "count must be refreshed every cycle"
    assert calls == [], "update() must not run before the AMP's refresh has elapsed"


async def test_a_run_still_in_flight_is_not_started_twice(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    started = threading.Event()
    release = threading.Event()
    calls = []

    def _blocking_update(process_list):
        calls.append(process_list)
        started.set()
        release.wait(timeout=5)

    amps._amps["python"].update = _blocking_update

    await amps.update()
    # Wait for the worker thread to have really entered `update()` before
    # asserting on `calls` — otherwise the assertion races the thread start.
    assert await asyncio.to_thread(started.wait, 5)
    await amps.update()  # second cycle while the first run is still blocked
    assert len(calls) == 1, "the in-flight guard must skip the second launch"

    release.set()
    await _settle(amps)


async def test_the_timer_is_not_consumed_by_a_skipped_cycle(cfg, procs):
    """The in-flight check must run BEFORE should_update(), which re-arms the
    timer as a side effect. Otherwise a skipped cycle silently eats a tick."""
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    release = threading.Event()

    def _blocking_update(process_list):
        release.wait(timeout=5)

    amp = amps._amps["python"]
    amp.update = _blocking_update

    # `_maybe_run` registers the in-flight task synchronously, so the guard is
    # armed as soon as this returns — no need to yield to the event loop.
    await amps.update()
    assert "python" in amps._inflight

    should_update_calls = []
    original = amp.should_update
    amp.should_update = lambda: (should_update_calls.append(1), original())[1]
    await amps.update()
    assert should_update_calls == [], "should_update() must not be called while a run is in flight"

    release.set()
    await _settle(amps)


async def test_a_failing_amp_does_not_break_the_cycle(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    def _boom(process_list):
        raise RuntimeError("boom")

    amps._amps["python"].update = _boom
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1  # the cycle completed


async def test_a_malformed_process_entry_yields_no_match(cfg, procs):
    """v4's _build_amps_list assigns `ret` inside a try that catches
    KeyError, then returns it — turning a caught KeyError into an
    UnboundLocalError (glances/amps_list.py:123-140)."""
    procs([{"pid": 1, "name": "python3"}])  # no cpu_percent / memory_percent
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()  # must not raise
    await _settle(amps)
    assert amps._amps["python"].count() == 0


async def test_update_returns_every_loaded_amp(cfg, procs):
    procs([])
    amps = AmpsListV5(
        cfg(
            """
            [amp_a]
            enable=true
            refresh=3
            command=echo a

            [amp_b]
            enable=false
            refresh=3
            command=echo b
            """
        )
    )
    returned = await amps.update()
    await _settle(amps)
    assert [type(a).__module__ for a in returned] == ["glances.amps.default", "glances.amps.default"]
    assert len(returned) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_amps_list_v5.py -k "update or count or flight or timer or match" -v`
Expected: FAIL — `AttributeError: 'AmpsListV5' object has no attribute 'update'`

- [ ] **Step 3: Implement the update cycle**

In `glances/amps_list_v5.py`, add `asyncio` to the imports, add the `glances_processes` import at module level (`from glances.processes import glances_processes`), initialise the in-flight map in `__init__` right after `self._regex`:

```python
        # Tasks currently running an AMP's `update()` in a worker thread,
        # keyed like `_amps`. Guarantees at most ONE run in flight per AMP.
        self._inflight: dict[str, asyncio.Task] = {}
```

then append to the class:

```python
    # -------------------------------------------------------------- update

    async def update(self) -> list[GlancesAmp]:
        """Run one orchestration cycle and return every loaded AMP.

        Never awaits an AMP's own work: a due AMP is offloaded to a worker
        thread and this coroutine returns immediately with whatever results
        the AMPs have produced so far. Mirrors `AmpsList.update()` branch for
        branch, with two deliberate differences (design §5.2): the process
        count is computed inline instead of inside a spawned thread, and an
        AMP whose previous run is still in flight is skipped.
        """
        processlist = self._get_processlist()

        for name, amp in self._amps.items():
            if not amp.enable():
                continue

            pattern = self._regex.get(name)
            if pattern is None:
                # No regex configured: run every `refresh` seconds regardless
                # of any process, and never display a count (issue #1690).
                amp.set_count(0)
                self._maybe_run(name, amp, [])
                continue

            matching = self._match(pattern, processlist)
            amp.set_count(len(matching))

            if matching:
                self._maybe_run(name, amp, matching)
                continue

            # No match: v4 does NOT run the AMP on this branch. It only
            # surfaces the absence when the operator asked for a minimum.
            count_min = amp.count_min()
            if count_min is not None and count_min > 0:
                amp.set_result("No running process")

        return list(self._amps.values())

    def _get_processlist(self) -> list[dict[str, Any]]:
        """Read the shared process engine. Read-only — refreshing it is
        `processcount`'s job, exactly as in v4."""
        try:
            raw = glances_processes.get_list()
        except Exception as e:
            logger.debug("AMPS: cannot read the process list (%s)", e)
            return []
        return raw if isinstance(raw, list) else []

    @staticmethod
    def _match(pattern: re.Pattern[str], processlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Processes matching `pattern`, projected to what AMPs consume.

        Searches both `name` and the joined `cmdline` (kernel threads have no
        cmdline — see issue #1261). Returns an empty list when the process
        dicts are malformed; v4 raises `UnboundLocalError` there.
        """
        try:
            return [
                {"pid": p["pid"], "cpu_percent": p["cpu_percent"], "memory_percent": p["memory_percent"]}
                for p in processlist
                if pattern.search(p["name"])
                or ((cmdline := p.get("cmdline")) and pattern.search(" ".join(cmdline)))
            ]
        except (TypeError, KeyError) as e:
            logger.debug("AMPS: cannot build the AMP process list (%s)", e)
            return []

    def _maybe_run(self, name: str, amp: GlancesAmp, matching: list[dict[str, Any]]) -> None:
        """Offload `amp.update(matching)` to a thread if it is due and idle.

        ORDER MATTERS: the in-flight check comes first because
        `should_update()` re-arms and resets the AMP's timer as a side effect
        (glances/amps/amp.py:149-160). Checking it first and then bailing out
        on the in-flight guard would silently consume that tick and double the
        AMP's effective period.

        `amp.update()` is called directly rather than `update_wrapper()`: the
        count and the timer are decided here now. `update()` is the method the
        AMP contract requires a script to implement; `update_wrapper()` is v4
        plumbing that no AMP overrides.
        """
        if name in self._inflight:
            logger.debug("AMP %s: previous run still in flight — skipping this cycle", name)
            return
        if not amp.should_update():
            return

        task = asyncio.create_task(asyncio.to_thread(amp.update, matching))
        self._inflight[name] = task
        task.add_done_callback(lambda t, n=name: self._on_run_done(n, t))

    def _on_run_done(self, name: str, task: asyncio.Task) -> None:
        self._inflight.pop(name, None)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            logger.warning("AMP %s: update failed (%s)", name, exception)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_amps_list_v5.py -v`
Expected: PASS (all loader + update tests)

- [ ] **Step 5: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/amps_list_v5.py tests/test_amps_list_v5.py
.venv/bin/python -m ruff format glances/amps_list_v5.py tests/test_amps_list_v5.py
git add glances/amps_list_v5.py tests/test_amps_list_v5.py
```

---

## Task 5: `PluginModel` — projection and levels

**Files:**
- Create: `glances/plugins/amps/model_v5.py`
- Test: `tests/test_plugin_amps_v5.py`

**Interfaces:**
- Consumes: `AmpsListV5(config)` and `await amps_list.update() -> list[GlancesAmp]` from Tasks 3-4.
- Produces: `glances.plugins.amps.model_v5.PluginModel`, discovered by `main_v5.discover_plugin_classes()`. Store payload: `{"data": [{name, result, refresh, timer, count, countmin, countmax, regex}], "_levels": {<name>: {"count": {"level", "prominent"}}}, "time_since_update": …}` — Task 6's renderer consumes exactly that shape.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_amps_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `amps` plugin (collection)."""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

import pytest

from glances import amps_list_v5 as amps_module
from glances.config_v5 import GlancesConfigV5
from glances.plugins.amps.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def _make(body: str) -> GlancesConfigV5:
        xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
        xdg_conf.parent.mkdir(parents=True, exist_ok=True)
        xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
        monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        return GlancesConfigV5()

    return _make


@pytest.fixture
def procs(monkeypatch):
    def _set(processlist):
        monkeypatch.setattr(amps_module.glances_processes, "get_list", lambda: list(processlist), raising=False)

    return _set


async def _settle(plugin: PluginModel) -> None:
    while plugin._amps_list._inflight:
        await asyncio.gather(*list(plugin._amps_list._inflight.values()), return_exceptions=True)
        await asyncio.sleep(0)


def test_plugin_identity(store, cfg):
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    assert p.plugin_name == "amps"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is False
    assert p.SCHEDULE_AT_GLOBAL_REFRESH is True
    assert p._primary_key == "name"


def test_fields_description(store, cfg):
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    assert set(p.fields_description) == {
        "name",
        "result",
        "refresh",
        "timer",
        "count",
        "countmin",
        "countmax",
        "regex",
    }


async def test_no_amp_configured_publishes_an_empty_list(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    await p.update()
    assert store.get("amps", {}).get("data") == []


async def test_payload_shape(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await p.update()
    await _settle(p)
    await p.update()
    item = store.get("amps", {})["data"][0]
    assert item["name"] == "Conntrack"  # default AMP capitalises (v4 parity)
    assert item["result"].strip() == "tracked"
    assert item["refresh"] == 30.0
    assert item["count"] == 0
    assert item["regex"] is False


async def test_regex_field_is_true_when_configured(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await p.update()
    await _settle(p)
    assert store.get("amps", {})["data"][0]["regex"] is True


@pytest.mark.parametrize(
    ("count", "count_min", "count_max", "expected"),
    [
        (2, None, None, "ok"),          # nothing configured -> always ok
        (2, 1, 3, "ok"),                # inside the band
        (5, 1, 3, "warning"),           # above countmax
        (1, 2, 3, "warning"),           # below countmin, but still running
        (0, None, None, "ok"),          # no countmin configured
        (0, 0, None, "ok"),             # countmin explicitly 0
        (0, 1, None, "critical"),       # required but absent
        (None, 1, 2, None),             # unreachable in practice, no level
    ],
)
def test_count_level_ladder(count, count_min, count_max, expected):
    assert PluginModel._count_level(count, count_min, count_max) == expected


async def test_levels_are_keyed_by_amp_name(store, cfg, procs):
    procs([])
    p = PluginModel(store, cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncountmin=1\n"))
    await p.update()
    await _settle(p)
    levels = store.get("amps", {})["_levels"]
    assert levels["Python"]["count"]["level"] == "critical"
    assert levels["Python"]["count"]["prominent"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_amps_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.amps.model_v5'`

- [ ] **Step 3: Implement the model**

Create `glances/plugins/amps/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — AMPs plugin (collection, one item per configured AMP).

Port of `glances/plugins/amps/__init__.py` (v4). All the orchestration —
dynamic loading, per-AMP cadence, bounded execution — lives in
`glances/amps_list_v5.py`; this model only projects the AMP objects into the
store and computes the level of each AMP's process count.

`SCHEDULE_AT_GLOBAL_REFRESH = True`: every AMP owns its cadence through its
own `Timer`, so `[amps] refresh` would only throttle the PUBLICATION of
results the AMPs have already produced. Same reasoning as `ports`.

See docs/superpowers/specs/2026-08-02-glances-v5-g6c-amps-design.md.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.amps_list_v5 import AmpsListV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """Application Monitoring Processes (collection, primary key ``name``)."""

    plugin_name: ClassVar[str] = "amps"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 calls its own `get_alert()`, not `get_alert_log()`: the level colours
    # the TUI cell and is never written to the event history nor dispatched to
    # an action. Same family as `ports` and `processlist`.
    EMITS_ALERTS: ClassVar[bool] = False
    # Each AMP fires on its own `[amp_<name>] refresh`; the plugin's job is to
    # publish what they produced, promptly. See the module docstring.
    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        # `Amp.NAME`, not the config-section suffix: the default AMP
        # capitalises it (`[amp_dropbox]` -> `Dropbox`). v4 parity.
        "name": {"description": "AMP name.", "unit": "string", "primary_key": True},
        "result": {"description": "AMP result (a string, possibly multi-line).", "unit": "string"},
        "refresh": {"description": "AMP refresh interval.", "unit": "second"},
        "timer": {"description": "Time until next refresh.", "unit": "second"},
        "count": {"description": "Number of matching processes.", "unit": "number"},
        "countmin": {"description": "Minimum number of matching processes.", "unit": "number"},
        "countmax": {"description": "Maximum number of matching processes.", "unit": "number"},
        "regex": {"description": "True when a regex is configured for this AMP.", "unit": "bool"},
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)
        self._amps_list = AmpsListV5(config)

    async def _grab_stats(self) -> list:
        amps = await self._amps_list.update()
        return [
            {
                "name": amp.NAME,
                "result": amp.result(),
                "refresh": amp.refresh(),
                "timer": amp.time_until_refresh(),
                "count": amp.count(),
                "countmin": amp.count_min(),
                "countmax": amp.count_max(),
                "regex": amp.regex() is not None,
            }
            for amp in amps
        ]

    # ------------------------------------------------------------- levels
    #
    # BESPOKE, on purpose: the level of `count` depends on two OTHER fields
    # (`countmin` / `countmax`), which neither the base's numeric ladder nor
    # its categorical mapping can express. Same precedent as `ports`;
    # `base_v5.py` is deliberately NOT modified.

    @staticmethod
    def _count_level(count: Any, count_min: Any, count_max: Any) -> str | None:
        """Transposition of v4 `AmpsPlugin.get_alert`.

        An unconfigured AMP defaults both bounds to the observed count, which
        is what makes it always `ok`.
        """
        if count is None:
            return None
        if count_min is None:
            count_min = count
        if count_max is None:
            count_max = count
        try:
            count = int(count)
            count_min = int(count_min)
            count_max = int(count_max)
        except (TypeError, ValueError):
            return None
        if count > 0:
            return "ok" if count_min <= count <= count_max else "warning"
        return "ok" if count_min == 0 else "critical"

    def _derived_parameters(self) -> None:
        """Compute `_levels` from the process count of each AMP.

        REPLACES the base implementation: `count` is the only field that ever
        gets a level. Adding a `watched: True` field to `fields_description`
        would therefore be silently ineffective — wire it in here as well.

        Shape: `{<Amp.NAME>: {"count": {"level": …, "prominent": False}}}`.
        `prominent = False`: v4 colours the AMP name text, never a background.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name is None:
                continue
            level = self._count_level(item.get("count"), item.get("countmin"), item.get("countmax"))
            if level is None:
                continue
            self._levels[name] = {"count": {"level": level, "prominent": False}}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_amps_v5.py -v`
Expected: PASS

- [ ] **Step 5: Verify the plugin is discovered and registered**

Run: `.venv/bin/python -c "from glances.main_v5 import discover_plugin_classes; print([c.plugin_name for _, c in discover_plugin_classes()])"`
Expected: the printed list contains `amps`

- [ ] **Step 6: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/plugins/amps/model_v5.py tests/test_plugin_amps_v5.py
.venv/bin/python -m ruff format glances/plugins/amps/model_v5.py tests/test_plugin_amps_v5.py
git add glances/plugins/amps/model_v5.py tests/test_plugin_amps_v5.py
```

---

## Task 6: curses renderer

**Files:**
- Create: `glances/plugins/amps/render_curses_v5.py`
- Test: `tests/test_plugin_amps_render_curses_v5.py`

**Interfaces:**
- Consumes: the store payload shape produced by Task 5.
- Produces: `render(payload: dict, fields_desc: dict | None = None, view: dict | None = None) -> list[Row]`, auto-discovered by `curses_renderer_v5._discover_plugin_renderer`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_amps_render_curses_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `amps` curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.amps.render_curses_v5 import render


def _payload(items, levels=None):
    return {"data": items, "_levels": levels or {}}


def test_empty_payload_renders_nothing():
    assert render(_payload([])) == []


def test_amp_without_result_is_skipped():
    """v4 `msg_curse` skips an AMP whose result is still None."""
    rows = render(_payload([{"name": "Python", "result": None, "count": 1, "regex": True}]))
    assert rows == []


def test_no_title_row_deliberate_do_not_fix():
    """v4 `amps.msg_curse` emits no title and no column header — the block
    sits between `processcount` and `processlist` and reads as part of that
    run. The missing title is that continuity, not an oversight."""
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0%", "count": 1, "regex": True}]))
    assert len(rows) == 1
    assert rows[0].cells[0].text.strip() == "Python"


def test_three_columns_name_count_result():
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0% | MEM: 2.0%", "count": 2, "regex": True}]))
    assert len(rows) == 1
    assert [c.text.strip() for c in rows[0].cells] == ["Python", "2", "CPU: 1.0% | MEM: 2.0%"]


def test_count_column_is_blank_without_a_regex():
    rows = render(_payload([{"name": "Conntrack", "result": "tracked: 12", "count": 0, "regex": False}]))
    assert rows[0].cells[1].text.strip() == ""


def test_multiline_result_repeats_neither_name_nor_count():
    rows = render(_payload([{"name": "Systemd", "result": "Services\nactive: 3\nfailed: 1", "count": 1, "regex": True}]))
    assert len(rows) == 3
    assert [c.text.strip() for c in rows[0].cells] == ["Systemd", "1", "Services"]
    assert [c.text.strip() for c in rows[1].cells] == ["", "", "active: 3"]
    assert [c.text.strip() for c in rows[2].cells] == ["", "", "failed: 1"]


def test_name_is_coloured_from_the_count_level():
    rows = render(
        _payload(
            [{"name": "Python", "result": "CPU: 1.0%", "count": 0, "regex": True}],
            {"Python": {"count": {"level": "critical", "prominent": False}}},
        )
    )
    assert rows[0].cells[0].color is ColorRole.CRITICAL
    assert rows[0].cells[0].prominent is False


def test_missing_level_falls_back_to_default_colour():
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0%", "count": 1, "regex": True}]))
    assert rows[0].cells[0].color is ColorRole.DEFAULT


def test_continuation_rows_are_not_coloured():
    rows = render(
        _payload(
            [{"name": "Systemd", "result": "Services\nfailed: 1", "count": 0, "regex": True}],
            {"Systemd": {"count": {"level": "critical", "prominent": False}}},
        )
    )
    assert rows[0].cells[0].color is ColorRole.CRITICAL
    assert rows[1].cells[0].color is ColorRole.DEFAULT
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_amps_render_curses_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.amps.render_curses_v5'`

- [ ] **Step 3: Implement the renderer**

Create `glances/plugins/amps/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the amps plugin.

Mirror of v4 `amps.msg_curse()`: three columns — the AMP name on 16 chars,
the number of matching processes on 4, then the AMP result. A multi-line
result produces one row per line, with the name and count cells filled on
the first line only.

    Python           2    CPU: 1.0% | MEM: 2.0%
    Systemd          1    Services
                          active: 3

NO TITLE ROW and no column header — deliberate, v4 parity. The block sits
between `processcount` and `processlist` in `RIGHT_SLOT` and reads as part
of that run. `tests/test_plugin_amps_render_curses_v5.py::test_no_title_row_deliberate_do_not_fix`
locks it.

Divergence from v4: v4 marks the result line `splittable=True`, letting it
wrap. The v5 `Cell` has no such attribute, so an over-long result line is
clipped by curses instead. Adding wrapping to the shared renderer for a
single caller was ruled out of scope (design §7).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# v4 formats the AMP name with `{:<16}` and the count with `{:<4}`.
_NAME_COL_WIDTH = 16
_COUNT_COL_WIDTH = 4


def _level_role(entry: Any) -> tuple[ColorRole, bool]:
    if isinstance(entry, dict):
        return (_LEVEL_TO_ROLE.get(entry.get("level"), ColorRole.DEFAULT), bool(entry.get("prominent")))
    return (ColorRole.DEFAULT, False)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("data")
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)]
    if not items:
        return []

    levels = payload.get("_levels")
    if not isinstance(levels, dict):
        levels = {}

    rows: list[Row] = []
    for item in items:
        result = item.get("result")
        if result is None:
            # The AMP has not produced anything yet — v4 skips it entirely
            # rather than rendering an empty row.
            continue

        name = str(item.get("name") or "")
        # v4 hides the count for a regex-less AMP: there is nothing to count.
        count = item.get("count")
        count_text = "" if not item.get("regex") or count is None else str(count)

        item_levels = levels.get(item.get("name"))
        role, prominent = _level_role(item_levels.get("count") if isinstance(item_levels, dict) else None)

        first = True
        for line in str(result).split("\n"):
            rows.append(
                Row(
                    cells=[
                        Cell(
                            text=f"{name if first else '':<{_NAME_COL_WIDTH}}",
                            color=role if first else ColorRole.DEFAULT,
                            prominent=prominent if first else False,
                        ),
                        Cell(text=f"{count_text if first else '':<{_COUNT_COL_WIDTH}}"),
                        Cell(text=line),
                    ]
                )
            )
            first = False
    return rows
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_amps_render_curses_v5.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Lint and stage**

```bash
.venv/bin/python -m ruff check glances/plugins/amps/render_curses_v5.py tests/test_plugin_amps_render_curses_v5.py
.venv/bin/python -m ruff format glances/plugins/amps/render_curses_v5.py tests/test_plugin_amps_render_curses_v5.py
git add glances/plugins/amps/render_curses_v5.py tests/test_plugin_amps_render_curses_v5.py
```

---

## Task 7: close the CVE carry-forwards, full-suite verification and manual smoke

**Files:**
- Modify: `docs/architecture/glances-v5-architecture-decisions.md` (the CVE table rows for `CVE-2026-53925` and `GHSA-59fj-m2j6-hcxh`)
- Verify: the whole test suite, ruff, and a live run

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: nothing consumed by later tasks — this is the closing gate.

- [ ] **Step 1: Update the two CVE rows**

In `docs/architecture/glances-v5-architecture-decisions.md`, the `CVE-2026-53925` row currently ends its "v5 plan" cell with `Carry forward (AMP / actions port)`. Replace that cell with:

```
Done — actions (`ShellAction.allow_shell()`) and AMP (`AmpsListV5` builds the `args` shim from `[global] disable_config_exec`, so `GlancesAmp.allow_operators()` gates `secure_popen`) — G6C-amps
```

The `GHSA-59fj-m2j6-hcxh` row currently ends its cell with `Carry forward (actions ✅ / AMP port)`. Replace that cell with:

```
Done — actions ✅ (CVE-2026-68519) and AMP ✅ (G6C-amps): the v5 AMP runner keeps `secure_popen`'s restricted grammar (`&&`, `|`, `>` — no shell) and honours `--disable-config-exec`
```

- [ ] **Step 2: Run the full test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS, zero failures. Record the total count for the final review — Tasks 1-6 add roughly 45 tests to the pre-existing suite.

- [ ] **Step 3: Lint the whole diff**

```bash
.venv/bin/python -m ruff check glances/ tests/
.venv/bin/python -m ruff format --check glances/ tests/
```
Expected: clean.

- [ ] **Step 4: Manual smoke test**

Create a scratch config enabling two AMPs — one `command=`-based (default module) and one regex-only — then run the v5 TUI:

```bash
cat > /tmp/glances-amps-smoke.conf <<'EOF'
[global]
refresh=2

[amp_python]
enable=true
regex=.*python.*
refresh=3
countmin=1

[amp_conntrack]
enable=true
refresh=5
one_line=false
command=echo "amps smoke ok"
EOF
.venv/bin/python -m glances -C /tmp/glances-amps-smoke.conf
```

Verify, in the right column between the process count and the process list:
- `Python` with a matching-process count, coloured green while at least one Python process runs;
- `Conntrack` with `amps smoke ok` and a blank count column;
- kill every Python process (or set `regex=.*nosuchprocess.*`) and confirm `Python` turns red with `No running process`;
- confirm the block does not flicker or blank out between AMP refreshes — that is what `SCHEDULE_AT_GLOBAL_REFRESH` guarantees.

Then check the REST payload:

```bash
.venv/bin/python -m glances -w -C /tmp/glances-amps-smoke.conf &
sleep 5
curl -s http://localhost:61208/api/5/amps | python -m json.tool
```
Expected: a `data` list of two items with `name`, `result`, `count`, `regex`, and a `_levels` map keyed by AMP name.

- [ ] **Step 5: Stage the documentation change**

```bash
git add docs/architecture/glances-v5-architecture-decisions.md
git status --short
```

Expected staged set — and nothing else:

```
M  conf/glances.conf
M  docs/architecture/glances-v5-architecture-decisions.md
M  docs/aoa/amps.rst
M  glances/amps/amp.py
M  glances/amps/default/__init__.py
M  glances/amps/nginx/__init__.py
M  glances/amps/systemd/__init__.py
M  glances/amps/systemv/__init__.py
A  glances/amps_list_v5.py
M  glances/config_v5.py
A  glances/plugins/amps/model_v5.py
A  glances/plugins/amps/render_curses_v5.py
M  glances/secure.py
M  tests/test_amp_secure_popen.py
A  tests/test_amps_list_v5.py
M  tests/test_config_v5.py
A  tests/test_plugin_amps_render_curses_v5.py
A  tests/test_plugin_amps_v5.py
```

`glances/amps_list.py` and `glances/plugins/amps/__init__.py` must NOT appear — the v4 runtime is untouched. `NEWS.rst` must NOT appear. Do not commit: the maintainer commits.

---

## Deliverables for the release changelog (not written now — release time only)

- New optional config key `[amp_*] timeout` (documented, shipped commented; default unchanged: no timeout).
- Behaviour: one AMP execution in flight at a time (v4 started one per cycle unconditionally).
- Behaviour: long AMP result lines are clipped rather than wrapped.
- Fix: an AMP named after a stdlib module no longer shadows it (`sys.path` is no longer mutated).
- Fix: `UnboundLocalError` when the AMP process-match list fails to build.
- Security: AMP commands honour `--disable-config-exec` under v5 — CVE-2026-53925 / GHSA-59fj-m2j6-hcxh carry-forward closed.
