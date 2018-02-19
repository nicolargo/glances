
import angular from "angular";

import GlancesPluginSensorsController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginSensors", {
    controller: GlancesPluginSensorsController,
    controllerAs: "vm",
    templateUrl: template,
});
