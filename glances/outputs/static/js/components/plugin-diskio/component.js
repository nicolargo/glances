'use strict';

glancesApp.component('glancesPluginDiskio', {
    controller: GlancesPluginDiskioController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-diskio/view.html'
});
