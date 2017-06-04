'use strict';

glancesApp.component('glancesPluginIp', {
    controller: GlancesPluginIpController,
    controllerAs: 'vm',
    bindings: {
        arguments: '<'
    },
    templateUrl: 'components/plugin-ip/view.html'
});
