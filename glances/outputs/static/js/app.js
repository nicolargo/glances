/* global module */
if (module.hot) {
	module.hot.accept();
}

import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/jetbrains-mono/700.css";
import "../css/style.scss";

import { createApp } from "vue";
import App from "./App.vue";
import * as filters from "./filters.js";

const app = createApp(App);
app.config.globalProperties.$filters = filters;
app.mount("#app");
