
import angular from "angular";

import GlancesPluginDiskioController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginDiskio", {
    controller: GlancesPluginDiskioController,
    controllerAs: 'vm',
    templateUrl: template,
});
