'use strict';

import GlancesPluginPortsController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginPorts', {
    controller: GlancesPluginPortsController,
    controllerAs: 'vm',
    templateUrl: template,
});
