'use strict';

glancesApp.component('glancesPluginSystem', {
    controller: GlancesPluginSystemController,
    controllerAs: 'vm',
    bindings: {
        isDisconnected: '<'
    },
    templateUrl: 'components/plugin-system/view.html'
});
