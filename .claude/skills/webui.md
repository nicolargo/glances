# Skill: Build and Work with the WebUI

Build, update, or troubleshoot the Glances Vue.js WebUI.

## Instructions

### Build the WebUI
```bash
make webui
```
This runs `npm ci && npm run build` in `glances/outputs/static/`.

### Development workflow
1. Source files are in `glances/outputs/static/`
2. Built output goes to `glances/outputs/static/public/`
3. Stack: Vue.js + Bootstrap 5 + SCSS

### Audit and update dependencies
```bash
make webui-audit          # Run npm audit
make webui-audit-fix      # Fix audit issues and rebuild
make webui-update         # Update all JS dependencies and rebuild
```

### Run with WebUI
```bash
make run-webserver        # Start Glances web server on port 61208
```
Then open http://localhost:61208 in a browser.

### Design principles (from CLAUDE.md)
- Strict typographic consistency across all plugins
- Pixel-perfect sparkline alignment (CSS grid, fixed row heights)
- Footer = vertical alert list (up to 10 entries)
- No gauges — prefer sparklines with inline current value

### Troubleshooting
- If `npm ci` fails, check Node.js version (LTS required, currently 24.x in CI)
- If build artifacts are stale, delete `glances/outputs/static/public/` and rebuild
- The CI builds WebUI on `develop` branch only (see `.github/workflows/webui.yml`)
