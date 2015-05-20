var glancesApp = angular.module('glancesApp', ['ngRoute'])

.config(function($routeProvider, $locationProvider) {
    $routeProvider.when('/', {
        templateUrl : 'stats.html',
        controller : 'statsController'
    }).when('/:refresh_time', {
        templateUrl : 'stats.html',
        controller : 'statsController'
    });

    $locationProvider.html5Mode(true);
});
