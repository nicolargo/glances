'use strict';

glancesApp.component('glancesPluginNetwork', {
    controller: GlancesPluginNetworkController,
    controllerAs: 'vm',
    bindings: {
        arguments: '<'
    },
    templateUrl: 'components/plugin-network/view.html'
});
