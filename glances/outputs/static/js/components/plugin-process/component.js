'use strict';

glancesApp.component('glancesPluginProcess', {
    controller: GlancesPluginProcessController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-process/view.html'
});
