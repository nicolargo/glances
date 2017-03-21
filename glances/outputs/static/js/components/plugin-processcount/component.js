'use strict';

glancesApp.component('glancesPluginProcesscount', {
    controller: GlancesPluginProcesscountController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-processcount/view.html'
});
