'use strict';

glancesApp.component('glancesPluginSystem', {
    controller: GlancesPluginSystemController,
    controllerAs: 'vm',
    bindings: {
      stats: '<',
      isDisconnected: '<'
    },
    templateUrl: 'components/plugin-system/view.html'
});
