
import angular from "angular";

import GlancesController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glances", {
    controller: GlancesController,
    controllerAs: 'vm',
    bindings: {
        refreshTime: "<"
    },
    templateUrl: template
});
