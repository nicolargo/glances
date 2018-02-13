'use strict';

import GlancesPluginSystemController from './controller';
import template from './view.html';

export default angular.module('glancesApp').component('glancesPluginSystem', {
    controller: GlancesPluginSystemController,
    controllerAs: 'vm',
    templateUrl: template,
});
