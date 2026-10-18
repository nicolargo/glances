# Skill: Glances v5 — CI/CD and branch model

Use this skill when working on GitHub Actions, branch strategy, release
tagging, or any infrastructure that affects how `develop` (Glances v5) and
`support/glancesv4` (Glances v4) are built, tested, and released.

## Branch model (architecture §10)

```
master             ──────────────────────────────────────────► tagged stable releases
support/glancesv4  ──────────────────────────────────────────► v4 maintenance (4.5.x)
develop            ──── v5.0.0b1 → rc → v5.0.0 ──────────────► v5 development
```

| Branch | Purpose | PR target |
|---|---|---|
| `master` | Tagged stable releases only — never merge directly | — |
| `develop` | Glances v5 development | **v5 PRs** |
| `support/glancesv4` | Glances v4 maintenance: 4.5.x bugfixes and security fixes only | v4 PRs |

**Cutover (maintainer, 2026-10-10):** the former `develop` (v4) was
branched to `support/glancesv4`, then `develop-v5` was merged into
`develop` and deleted. The weekly `develop → develop-v5` merge job was
deleted with it.

## PR routing rule

| Type of change | Target branch |
|---|---|
| v5 work (feature, bugfix, plugin, exporter, action) | `develop` |
| v5 security fix | `develop` |
| Documentation change for v5 | `develop` |
| v4 bugfix (4.5.x) | `support/glancesv4` |
| v4 security fix | `support/glancesv4` |
| Documentation change for v4 | `support/glancesv4` |

Nothing propagates automatically between the two branches. A fix that
applies to both v4 and v5 is two PRs, one per branch, each written
against that branch's code.

## Release tagging

| Stage | Tag format | Source branch | PyPI |
|---|---|---|---|
| Alpha | — | — | **No** (maintainer, 2026-10-03) |
| Beta | `v5.0.0b1`, `v5.0.0b2`, … | `develop` | Yes — PyPI pre-release, the first published v5 |
| Release candidate | `v5.0.0rc1`, … | `develop` | Yes — PyPI pre-release |
| Final | `v5.0.0` | `develop` | Yes |
| v4 hotfix | `v4.5.x` | `support/glancesv4` | Yes |

`build.yml` publishes to PyPI on any tag (a pre-release tag such as
`v5.0.0b1` publishes a PyPI pre-release) and to TestPyPI on every push
to `develop`. A pre-release tag (`a`, `b` or `rc` suffix) never moves the
Docker `latest` / `latest-full` tags.

## GitHub Actions guards — known pitfalls

### `build_docker.yml` — empty matrix is a silent failure

The `build_docker` job of `ci.yml` combines branch exclusion **and** event
type (and `build_docker.yml` skips its build job when the tag list is
`[]`). A dynamic matrix with zero entries fails silently without this
guard:

```yaml
if: >
  github.event_name != 'pull_request' &&
  (github.ref == 'refs/heads/develop' || startsWith(github.ref, 'refs/tags/'))
```

The `master` branch does not trigger a Docker build. Without the
condition above, an empty matrix evaluates to "no job ran" and CI reports
green — which is **wrong**. Always combine exclusion conditions with
`&&` rather than cascading them.

### General workflow rules

- **Be explicit about the trigger branch and event type** in the `if:`
  clause.
- **Guard-clause every job that depends on a dynamic matrix** — an empty
  matrix is a failure, not a no-op.
- **Combine exclusion conditions with `&&`**, not in cascade.

## Test execution

One suite: `tests/test_*.py` (pytest, `pytest-asyncio` auto mode — see
`pyproject.toml` `[tool.pytest.ini_options]`), plus the WebUI JavaScript
tests `tests/js/*.mjs` (`make test-js`, run by `tests/test_webui_js.py`).
`.github/workflows/test.yml` runs:

- **Linux** — the whole suite (`python -m pytest tests/`) on every
  supported Python, including the JavaScript tests and the WebUI browser
  tests (`tests/test_webui_browser*.py`, Playwright + Chromium);
- **Windows, macOS, FreeBSD** — the whole suite; the tests specific to Linux
  (curses TUI, `/proc`) are skipped there.

`tests/test_imports.py` fails when any code or test imports a `glances`
module that does not exist (the deleted v4 modules included).

A v5 release is not valid if any migrated v4 test fails or has been
silently dropped (architecture §9).

## Linting and formatting

```bash
make pre-commit  # every pre-commit hook (ruff, gitleaks, shellcheck, …)
make lint        # ruff check
make format      # ruff format
```

`make pre-commit` must be green before merge (it supersedes
`make lint && make format`; hooks in `.pre-commit-config.yaml`). CI runs
`ruff check` in `test.yml` (`source-code-checks`).

## Container builds

| Workflow | Trigger | Output |
|---|---|---|
| `build_docker.yml` | `develop` push (`dev` image) or tag | Docker images (Glances v5) on Docker Hub / GHCR; a pre-release tag never moves `latest` |
| `build.yml` | Pushes to `develop` / `master` and tags | Wheels and source dist; PyPI on tags, TestPyPI on `develop` |
| `webui.yml` | `develop` push | Vue.js bundle (`public/glances.js`, `public/browser.js`), committed by CI |

Refer to `@.claude/docs/commands.md` for the canonical list of `make`
targets and local development commands.

## Snapcraft (system packaging)

- **Strict confinement** blocks host file access at the `open()` stage,
  not at `read()`. Wrap `open()` calls in `try/except`, not just the
  body of the `with` block (project CLAUDE.md, Snap section).
- Prefer auto-approved plugs to avoid manual store review.

## What's deferred

- **Helm chart for v5** — Phase 3 (when v5 has feature parity for server mode)

Done at the cutover: the v5 beta PyPI release (`build.yml`, any tag
publishes; `v5.0.0b1` is a PyPI pre-release) and the Docker images, which
now run Glances v5 (`python -m glances`).

## Module path

This skill is documentation-only. Workflows live in:

```
.github/workflows/ci.yml                 # Entry point: PRs to develop, pushes to develop/master, v* tags
.github/workflows/build_docker.yml       # Docker — empty-matrix guard above
.github/workflows/build.yml              # Wheels / sdist, PyPI + TestPyPI
.github/workflows/test.yml               # Test matrix (Linux, Windows, macOS, FreeBSD)
.github/workflows/quality.yml            # Code quality
.github/workflows/webui.yml              # WebUI bundle
.github/workflows/cyber.yml              # Security scans
.github/workflows/inactive_issues.yml    # Daily: label inactive issues
.github/workflows/needs_contributor.yml  # Comment on the "needs contributor" label
```
