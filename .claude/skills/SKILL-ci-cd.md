# Skill: Glances v5 — CI/CD and branch model

Use this skill when working on GitHub Actions, branch strategy, release
tagging, or any infrastructure that affects how `develop-v5` is built,
tested, and released.

## Branch model (architecture §10)

```
main          ──────────────────────────────────────────────────► (v4 stable releases)
develop       ──────────────────────────────────────────────────► (v4 bugfixes & security)
develop-v5    ──┬──────┬──────┬──────┬──────────────────────────► (v5 development)
                │      │      │      │
             weekly  alpha  alpha  alpha  …→ beta → rc → merge develop
             merge   0.1    0.2    0.3
```

| Branch | Purpose | PR target |
|---|---|---|
| `main` | Tagged v4 stable releases only — never merge directly | — |
| `develop` | v4 bugfixes and security fixes | v4 PRs |
| `develop-v5` | v5 development (Phase 0 → v5.0.0-rc) | **v5 PRs** |

## PR routing rule

| Type of change | Target branch |
|---|---|
| v4 bugfix | `develop` |
| v4 security fix | `develop` |
| v5 work (any phase) | `develop-v5` |
| v5 plugin / exporter / action | `develop-v5` |
| Documentation change for v5 | `develop-v5` |
| Documentation change for v4 | `develop` |

A v4 fix that lands on `develop` is automatically propagated to
`develop-v5` via the weekly merge job (see below). Contributors should
**not** open the same PR against both branches.

## Weekly automated merge (`develop → develop-v5`)

Workflow: `.github/workflows/weekly_merge_develop_to_v5.yml`

- Cron: every Monday at 06:00 UTC
- Clean merge → pushed directly to `develop-v5`
- Conflict → opens a tracking issue and pushes a branch for manual
  resolution

**Resolution policy.** Conflicts are resolved **immediately**, never
accumulated. Restructured files (e.g. v4 `glances/foo.py` vs. v5
`glances/foo_v5.py`) are the most common source. The maintainer reviews
and resolves within 48 hours of the cron run.

## Release tagging

| Stage | Tag format | Source branch | PyPI |
|---|---|---|---|
| Alpha | `5.0.0a1`, `5.0.0a2`, … | `develop-v5` | Yes (early feedback) |
| Beta | `5.0.0b1`, `5.0.0b2`, … | `develop-v5` | Yes |
| Release candidate | `5.0.0rc1`, … | `develop-v5` | Yes |
| Final | `5.0.0` | `develop` (after `develop-v5 → develop` merge) | Yes |

The final merge `develop-v5 → develop` happens at v5.0.0-rc stage, after
all plugins, exporters, and migrated tests are green.

## GitHub Actions guards — known pitfalls

### `build_docker.yml` — empty matrix is a silent failure

The workflow's trigger condition combines branch exclusion **and** event
type. A dynamic matrix with zero entries fails silently without this
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

Two complementary suites live in CI:

- **v4 tests** — `tests/unitest_*.py` (legacy `unittest`-based). Run
  unchanged on `develop` and `develop-v5` until they are migrated one by
  one to `tests/test_*_v5.py`.
- **v5 tests** — `tests/test_*_v5.py` (pytest-native, `pytest-asyncio`
  auto mode). New tests for v5 components only. See `pyproject.toml`
  `[tool.pytest.ini_options]`.

A v5 release is not valid if any migrated v4 test fails or has been
silently dropped (architecture §9).

## Linting and formatting

```bash
make lint        # ruff check
make format      # ruff format
```

Both commands must be green before merge. The pre-commit hook is not
configured — contributors run `make lint && make format` locally.

## Container builds

| Workflow | Trigger | Output |
|---|---|---|
| `build_docker.yml` | `develop` push or tag | Docker images on Docker Hub / GHCR |
| `build.yml` | All pushes to v4/v5 dev branches | Wheels and source dist |
| `webui.yml` | Changes under `glances/outputs/static/` | Vue.js bundle |

Refer to `@.claude/docs/commands.md` for the canonical list of `make`
targets and local development commands.

## Snapcraft (system packaging)

- **Strict confinement** blocks host file access at the `open()` stage,
  not at `read()`. Wrap `open()` calls in `try/except`, not just the
  body of the `with` block (project CLAUDE.md, Snap section).
- Prefer auto-approved plugs to avoid manual store review.

## What's deferred

- **Concrete CI workflow for the v5 alpha PyPI release** — Phase 1 (when first alpha ships)
- **`glances-v5` Docker image** — Phase 2 (when v5 has feature parity for standalone mode)
- **Helm chart for v5** — Phase 3 (when v5 has feature parity for server mode)

## Module path

This skill is documentation-only. Workflows live in:

```
.github/workflows/build_docker.yml             # Docker — has the matrix guard above
.github/workflows/build.yml                    # Wheels / sdist
.github/workflows/ci.yml                       # Lint + tests
.github/workflows/test.yml                     # Test matrix
.github/workflows/quality.yml                  # Code quality
.github/workflows/webui.yml                    # WebUI bundle
.github/workflows/cyber.yml                    # Security scans
.github/workflows/weekly_merge_develop_to_v5.yml   # Weekly auto-merge develop → develop-v5
```
