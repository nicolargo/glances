'use strict';

glancesApp.component('glancesPluginPercpu', {
    controller: GlancesPluginPercpuController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-percpu/view.html'
});
