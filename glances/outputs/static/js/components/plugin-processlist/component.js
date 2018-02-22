
import angular from "angular";

import GlancesPluginProcesslistController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginProcesslist", {
    controller: GlancesPluginProcesslistController,
    controllerAs: "vm",
    bindings: {
        sorter: "<"
    },
    templateUrl: template,
});
