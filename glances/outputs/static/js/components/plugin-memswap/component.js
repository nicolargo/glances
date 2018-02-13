'use strict';

import GlancesPluginMemswapController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginMemswap', {
    controller: GlancesPluginMemswapController,
    controllerAs: 'vm',
    templateUrl: template,
});
