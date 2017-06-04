'use strict';

glancesApp.component('glancesPluginProcesslist', {
    controller: GlancesPluginProcesslistController,
    controllerAs: 'vm',
    bindings: {
        sorter: '<'
    },
    templateUrl: 'components/plugin-processlist/view.html'
});
