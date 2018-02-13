'use strict';

import GlancesPluginPercpuController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginPercpu', {
    controller: GlancesPluginPercpuController,
    controllerAs: 'vm',
    templateUrl: template,
});
