'use strict';

glancesApp.component('glancesPluginIp', {
    controller: GlancesPluginIpController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-ip/view.html'
});
