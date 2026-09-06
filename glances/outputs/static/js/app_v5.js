// Glances v5 WebUI entry point.
//
// The `template:` option G9-1 used needs Vue's template compiler, which the
// runtime-only build does not carry -- that shipped a silently blank page.
// Single-file components are compiled by vue-loader at build time, so no
// `template:` string survives into the bundle, the runtime build is enough,
// and G9-3 dropped the webpack alias that pulled the full build in.

import { createApp } from "vue";
import "../css/v5.css";
import AppShell from "./v5/AppShell.vue";

createApp(AppShell).mount("#app");
