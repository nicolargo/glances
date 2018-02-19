
import angular from "angular";

import GlancesPluginCpuController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginCpu", {
    controller: GlancesPluginCpuController,
    controllerAs: 'vm',
    templateUrl: template,
});
