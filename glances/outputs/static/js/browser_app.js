// Glances v5 WebUI — the browser page's entry point (P3-6), served at
// /browser by `glances -s --browser`. Same stylesheet as the main page.

import { createApp } from "vue";
import "../css/glances.css";
import BrowserPage from "./BrowserPage.vue";

createApp(BrowserPage).mount("#app");
