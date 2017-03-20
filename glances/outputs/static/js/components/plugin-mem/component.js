'use strict';

glancesApp.component('glancesPluginMem', {
    controller: GlancesPluginMemController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-mem/view.html'
});
