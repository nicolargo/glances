// Glances v5 WebUI -- the blocks `--full-quicklook` hides.
//
// A mirror of `_FULL_QUICKLOOK_HIDDEN` (glances/outputs/curses_renderer_v5.py:89):
// the browser cannot import Python. `load` and `percpu` are deliberately NOT
// in this set (curses_renderer_v5.py:86). Kept in its own module, not part of
// AppShell.vue, because a `.vue` file cannot be imported under node --
// tests/test_webui_v5_full_quicklook_drift.py fails on drift, the same reason
// degrade.js is a `.js` module and not part of the shell.
export const FULL_QUICKLOOK_HIDDEN = new Set(["cpu", "npu", "mpp", "gpu", "mem", "memswap"]);
