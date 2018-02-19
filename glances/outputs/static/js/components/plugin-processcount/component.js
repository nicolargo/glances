
import angular from "angular";

import GlancesPluginProcesscountController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginProcesscount", {
    controller: GlancesPluginProcesscountController,
    controllerAs: "vm",
    bindings: {
        sorter: "<"
    },
    templateUrl: template,
});
