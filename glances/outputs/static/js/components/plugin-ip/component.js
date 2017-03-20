'use strict';

glancesApp.component('glancesPluginIp', {
    controller: GlancesPluginIpController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-ip/view.html'
});
