'use strict';

glancesApp.component('glances', {
    controller: GlancesController,
    bindings: {
      arguments: '<',
      config: '<',
      help: '<'
    },
    controllerAs: 'vm',
    templateUrl: 'components/glances/view.html'
});
