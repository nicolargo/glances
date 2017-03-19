'use strict';

glancesApp.component('glancesPluginCpu', {
    controller: GlancesPluginCpuController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-cpu/view.html'
});
