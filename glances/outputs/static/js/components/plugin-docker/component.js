
import angular from "angular";

import GlancesPluginDockerController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginDocker", {
    controller: GlancesPluginDockerController,
    controllerAs: "vm",
    templateUrl: template,
});
