
import angular from "angular";

import GlancesPluginCloudController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginCloud", {
    controller: GlancesPluginCloudController,
    controllerAs: 'vm',
    templateUrl: template,
});
