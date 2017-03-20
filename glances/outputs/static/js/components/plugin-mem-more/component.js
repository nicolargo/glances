'use strict';

glancesApp.component('glancesPluginMemMore', {
    controller: GlancesPluginMemMoreController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-mem-more/view.html'
});
