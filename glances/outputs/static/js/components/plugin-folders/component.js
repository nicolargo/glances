
import angular from "angular";

import GlancesPluginFsController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesPluginFolders", {
    controller: GlancesPluginFsController,
    controllerAs: "vm",
    templateUrl: template,
});
