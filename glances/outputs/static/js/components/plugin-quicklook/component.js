'use strict';

glancesApp.component('glancesPluginQuicklook', {
    controller: GlancesPluginQuicklookController,
    controllerAs: 'vm',
    bindings: {
        stats: '<',
        arguments: '<'
    },
    templateUrl: 'components/plugin-quicklook/view.html'
});
