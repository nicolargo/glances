'use strict';

glancesApp.component('glancesPluginProcesslist', {
    controller: GlancesPluginProcesslistController,
    controllerAs: 'vm',
    bindings: {
        arguments: '<',
        sorter: '<'
    },
    templateUrl: 'components/plugin-processlist/view.html'
});
