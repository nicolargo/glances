
import angular from "angular";

import GlancesPluginQuicklookController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginQuicklook", {
    controller: GlancesPluginQuicklookController,
    controllerAs: "vm",
    templateUrl: template,
});
