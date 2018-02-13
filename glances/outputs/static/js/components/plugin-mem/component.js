'use strict';

import GlancesPluginMemController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginMem', {
    controller: GlancesPluginMemController,
    controllerAs: 'vm',
    templateUrl: template,
});
