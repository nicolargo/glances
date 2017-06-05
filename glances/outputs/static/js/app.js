var glancesApp = angular.module('glancesApp', ['glances.config', 'cfp.hotkeys'])

.value('CONFIG', {})
.value('ARGUMENTS', {})

.config(function(hotkeysProvider) {
  hotkeysProvider.useNgRoute = false;
  hotkeysProvider.includeCheatSheet = false;
})

.run(function($rootScope, GlancesStats) {
      $rootScope.title = "Glances";

      GlancesStats.init();
});
