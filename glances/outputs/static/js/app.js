var glancesApp = angular.module('glancesApp', ['ngRoute', 'glances.config'])

.config(function($routeProvider, $locationProvider) {
    $routeProvider.when('/', {
        template : '<glances arguments="arguments"></glances>',
        controller : 'statsController',
        resolve: {
            help: function(GlancesStats) {
                return GlancesStats.getHelp();
            },
            config: function(GlancesStats) {
                return GlancesStats.getConfig();
            },
            arguments: function(GlancesStats) {
                return GlancesStats.getArguments();
            }
        }
    });
})
.run(function($rootScope) {
      $rootScope.title = "Glances";
});
