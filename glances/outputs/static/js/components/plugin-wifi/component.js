'use strict';

glancesApp.component('glancesPluginWifi', {
    controller: GlancesPluginWifiController,
    controllerAs: 'vm',
    bindings: {
        stats: '<'
    },
    templateUrl: 'components/plugin-wifi/view.html'
});
