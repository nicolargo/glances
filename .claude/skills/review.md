# Skill: Review Code Changes

Review the current changes (staged or unstaged) against Glances project guidelines.

## Instructions

1. Get the diff to review:
   - If the user provides a PR number, fetch it with `gh pr diff <number>`
   - Otherwise, use `git diff` (unstaged) and `git diff --cached` (staged)
   - If a branch is specified, use `git diff <base>...<branch>`

2. Check each item on this checklist:

### Correctness
- [ ] No dead code introduced (unused functions, imports, variables)
- [ ] Exception handling wraps the right operation (e.g., `open()` not `read()` for Snap confinement)
- [ ] No silent exception swallowing (`except: pass` or bare `except`)
- [ ] No O(n²) patterns where O(n) is possible (linear search in a loop → use dict/set)
- [ ] No `list.pop(0)` for queues → suggest `collections.deque(maxlen=N)`

### Security
- [ ] No credentials/secrets exposed in plain text
- [ ] No new endpoints without considering auth implications
- [ ] Sensitive config keys filtered from API responses
- [ ] No command injection, XSS, or SQL injection vectors

### Compatibility
- [ ] Default behaviour unchanged (or breaking change explicitly documented)
- [ ] Cross-platform considerations (Linux/macOS/Windows)
- [ ] Configuration keys documented in `conf/glances.conf`

### Style
- [ ] Code passes `make format && make lint`
- [ ] No unnecessary comments, docstrings, or type annotations on unchanged code
- [ ] Plugin/export conventions followed (class naming, auto-discovery, fields_description)

3. Report findings grouped by severity:
   - **Blocking** — must fix before merge
   - **Suggestion** — improvement, not required
   - **Nit** — style/cosmetic, optional

4. Use the tone from CLAUDE.md: acknowledge quality, label problems as "blocking concern", invite collaboration.
