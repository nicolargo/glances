'use strict';

glancesApp.component('glancesPluginNetwork', {
    controller: GlancesPluginNetworkController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-network/view.html'
});
