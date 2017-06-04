var glancesApp = angular.module('glancesApp', ['ngRoute', 'glances.config', 'fps.hotkeys'])

.value('CONFIG', {})
.value('ARGUMENTS', {})

.run(function($rootScope) {
      $rootScope.title = "Glances";
});
