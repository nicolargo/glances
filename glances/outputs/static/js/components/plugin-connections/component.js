
import angular from "angular";

import GlancesPluginConnectionsController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginConnections", {
    controller: GlancesPluginConnectionsController,
    controllerAs: "vm",
    templateUrl: template,
});
