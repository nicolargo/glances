
import angular from "angular";

import GlancesPluginGpuController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginGpu", {
    controller: GlancesPluginGpuController,
    controllerAs: "vm",
    templateUrl: template,
});
