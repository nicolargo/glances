var glancesApp = angular.module('glancesApp', ['ngRoute'])

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

    $locationProvider.html5Mode(true);
})
.run(function($rootScope) {
      $rootScope.title = "Glances";
});
