/* global module */
if (module.hot) {
    module.hot.accept();
}

import '../css/custom.scss';
import '../css/style.scss';

import * as bootstrap from 'bootstrap';

import { createApp } from 'vue';
import App from './Browser.vue';
import * as filters from "./filters.js";

const app = createApp(App);
app.config.globalProperties.$filters = filters;
app.mount('#browser');
