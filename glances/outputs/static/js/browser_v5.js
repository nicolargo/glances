// Glances v5 WebUI — the browser page's entry point (P3-6), served at
// /browser by `glances-v5 -s --browser`. Same stylesheet as the main page.

import { createApp } from "vue";
import "../css/v5.css";
import BrowserPage from "./v5/BrowserPage.vue";

createApp(BrowserPage).mount("#app");
