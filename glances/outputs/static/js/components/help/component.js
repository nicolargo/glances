'use strict';

glancesApp.component('glancesHelp', {
    controller: GlancesHelpController,
    controllerAs: 'vm',
    bindings: {
      help: '<',
    },
    templateUrl: 'components/help/view.html'
});
