var glancesApp = angular.module('glancesApp', ['ngRoute'])

.config(function($routeProvider, $locationProvider) {
    $routeProvider.when('/:refresh_time?', {
        templateUrl : 'stats.html',
        controller : 'statsController',
        resolve: {
            help: function(GlancesStats) {
                return GlancesStats.getHelp();
            },
            arguments: function(GlancesStats, $route) {
                return GlancesStats.getArguments().then(function(arguments) {
                    var refreshTimeRoute = parseInt($route.current.params.refresh_time);
                    if (!isNaN(refreshTimeRoute) && refreshTimeRoute > 1) {
                        arguments.time = refreshTimeRoute;
                    }

                    return arguments;
                });
            }
        }
    });

    $locationProvider.html5Mode(true);
})
.run(function($rootScope) {
      $rootScope.title = "Glances";
});
