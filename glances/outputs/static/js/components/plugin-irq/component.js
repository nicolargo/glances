'use strict';

import GlancesPluginIrqController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginIrq', {
    controller: GlancesPluginIrqController,
    controllerAs: 'vm',
    templateUrl: template,
});
