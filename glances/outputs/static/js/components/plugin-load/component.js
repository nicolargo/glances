
import angular from "angular";

import GlancesPluginLoadController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginLoad", {
    controller: GlancesPluginLoadController,
    controllerAs: "vm",
    templateUrl: template,
});
