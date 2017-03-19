'use strict';

glancesApp.component('glancesPluginUptime', {
    controller: GlancesPluginUptimeController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-uptime/view.html'
});
