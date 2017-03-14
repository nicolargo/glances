'use strict';

glancesApp.component('glancesPluginLoad', {
    controller: GlancesPluginLoadController,
    controllerAs: 'vm',
    bindings: {
      stats: '<',
    },
    templateUrl: 'components/plugin-load/view.html'
});
