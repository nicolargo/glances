'use strict';

glancesApp.component('glancesPluginProcesscount', {
    controller: GlancesPluginProcesscountController,
    controllerAs: 'vm',
    bindings: {
        sorter: '<'
    },
    templateUrl: 'components/plugin-processcount/view.html'
});
