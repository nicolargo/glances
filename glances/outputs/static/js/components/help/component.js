
import angular from "angular";

import GlancesHelpController from "./controller";
import template from "./view.html";

export default angular.module("glancesApp").component("glancesHelp", {
    controller: GlancesHelpController,
    controllerAs: 'vm',
    templateUrl: template,
});
