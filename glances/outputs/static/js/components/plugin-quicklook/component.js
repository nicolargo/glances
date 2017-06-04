'use strict';

glancesApp.component('glancesPluginQuicklook', {
    controller: GlancesPluginQuicklookController,
    controllerAs: 'vm',
    bindings: {
        arguments: '<'
    },
    templateUrl: 'components/plugin-quicklook/view.html'
});
