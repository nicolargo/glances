'use strict';

glancesApp.component('glancesPluginProcesscount', {
    controller: GlancesPluginProcesscountController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        sorter: '<'
    },
    templateUrl: 'components/plugin-processcount/view.html'
});
