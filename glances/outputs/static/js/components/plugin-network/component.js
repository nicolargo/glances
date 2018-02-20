
import angular from "angular";

import GlancesPluginNetworkController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginNetwork", {
    controller: GlancesPluginNetworkController,
    controllerAs: "vm",
    templateUrl: template,
});
