
import angular from "angular";

import GlancesPluginIpController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginIp", {
    controller: GlancesPluginIpController,
    controllerAs: "vm",
    templateUrl: template,
});
