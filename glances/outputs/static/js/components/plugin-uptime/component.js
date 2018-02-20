
import angular from "angular";

import GlancesPluginUptimeController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginUptime", {
    controller: GlancesPluginUptimeController,
    controllerAs: "vm",
    templateUrl: template,
});
