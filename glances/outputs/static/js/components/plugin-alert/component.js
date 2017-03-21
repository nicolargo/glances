'use strict';

glancesApp.component('glancesPluginAlert', {
    controller: GlancesPluginAlertController,
    controllerAs: 'vm',
    bindings: {
      stats: '<'
    },
    templateUrl: 'components/plugin-alert/view.html'
});
