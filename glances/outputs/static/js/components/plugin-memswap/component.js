'use strict';

glancesApp.component('glancesPluginMemswap', {
    controller: GlancesPluginMemswapController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-memswap/view.html'
});
