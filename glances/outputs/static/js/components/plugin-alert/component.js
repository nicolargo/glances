
import angular from "angular";

import GlancesPluginAlertController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginAlert", {
    controller: GlancesPluginAlertController,
    controllerAs: 'vm',
    templateUrl: template,
});
