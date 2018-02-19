
import angular from "angular";

import GlancesPluginWifiController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginWifi", {
    controller: GlancesPluginWifiController,
    controllerAs: "vm",
    templateUrl: template,
});
