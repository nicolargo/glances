'use strict';

import GlancesPluginIpController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginIp', {
    controller: GlancesPluginIpController,
    controllerAs: 'vm',
    templateUrl: template,
});
