'use strict';

glancesApp.component('glancesPluginFs', {
    controller: GlancesPluginFsController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-fs/view.html'
});
