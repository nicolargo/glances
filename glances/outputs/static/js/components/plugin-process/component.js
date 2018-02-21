
import angular from "angular";

import GlancesPluginProcessController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginProcess", {
    controller: GlancesPluginProcessController,
    controllerAs: "vm",
    templateUrl: template,
});
