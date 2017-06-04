'use strict';

glancesApp.component('glancesPluginFs', {
    controller: GlancesPluginFsController,
    controllerAs: 'vm',
    bindings: {
        arguments: '<'
    },
    templateUrl: 'components/plugin-fs/view.html'
});
