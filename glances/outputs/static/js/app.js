// Glances v5 WebUI entry point.
//
// The `template:` option G9-1 used needs Vue's template compiler, which the
// runtime-only build does not carry -- that shipped a silently blank page.
// Single-file components are compiled by vue-loader at build time, so no
// `template:` string survives into the bundle, the runtime build is enough,
// and G9-3 dropped the webpack alias that pulled the full build in.

import { createApp } from "vue";
import "../css/glances.css";
import AppShell from "./AppShell.vue";
import { vHistory } from "./history.js";

// Global, so a plugin writes `v-history` on a cell without registering it.
createApp(AppShell).directive("history", vHistory).mount("#app");
