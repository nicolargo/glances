
import angular from "angular";

import GlancesPluginRaidController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginRaid", {
    controller: GlancesPluginRaidController,
    controllerAs: "vm",
    templateUrl: template,
});
