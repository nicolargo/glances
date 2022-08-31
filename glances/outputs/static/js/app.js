/* global module */
if (module.hot) {
    module.hot.accept();
}

import '../css/bootstrap.less';
import '../css/style.scss';

import { createApp } from 'vue';
import App from './App.vue';
import * as filters from "./filters.js";

const app = createApp(App);
app.config.globalProperties.$filters = filters;
app.mount('#app');
