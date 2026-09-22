// Glances v5 WebUI -- the blocks `--full-quicklook` hides.
//
// A mirror of `_FULL_QUICKLOOK_HIDDEN` (glances/outputs/curses_renderer_v5.py:91):
// the browser cannot import Python. The TUI derives it as `TOP_SLOT` minus
// `quicklook` -- EVERY sibling, so the mode means quicklook alone, full width
// (a deliberate v4 divergence, `…decisions.md` §10 "Reversed decision -- full
// quicklook", 2026-09-22; `load` and `percpu` used to be exempt here).
//
// This list is the TUI's TOP_SLOT order, minus `quicklook`. Kept in its own
// module, not part of AppShell.vue, because a `.vue` file cannot be imported
// under node -- tests/test_webui_v5_full_quicklook_drift.py fails on drift,
// the same reason degrade.js is a `.js` module and not part of the shell.
export const FULL_QUICKLOOK_HIDDEN = new Set([
	"cpu",
	"percpu",
	"npu",
	"mpp",
	"gpu",
	"mem",
	"memswap",
	"load",
]);
