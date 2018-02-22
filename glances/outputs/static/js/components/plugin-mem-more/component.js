
import angular from "angular";

import GlancesPluginMemMoreController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginMemMore", {
    controller: GlancesPluginMemMoreController,
    controllerAs: "vm",
    templateUrl: template,
});
