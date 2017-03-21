'use strict';

glancesApp.component('glancesPluginPorts', {
    controller: GlancesPluginPortsController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-ports/view.html'
});
