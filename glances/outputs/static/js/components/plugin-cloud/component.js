'use strict';

glancesApp.component('glancesPluginCloud', {
    controller: GlancesPluginCloudController,
    controllerAs: 'vm',
    bindings: {
      stats: '<'
    },
    templateUrl: 'components/plugin-cloud/view.html'
});
