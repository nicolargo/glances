'use strict';

glancesApp.component('glances', {
    controller: GlancesController,
    bindings: {
      arguments: '<'
    },
    controllerAs: 'vm',
    templateUrl: 'components/glances/view.html'
});
