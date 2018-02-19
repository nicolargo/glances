
import angular from "angular";

import GlancesPluginAmpsController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginAmps", {
    controller: GlancesPluginAmpsController,
    controllerAs: 'vm',
    templateUrl: template,
});
