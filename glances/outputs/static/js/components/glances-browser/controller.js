'use strict';

function GlancesBrowserController($scope, GlancesBrowser, $window) {
    var vm = this;
    vm.dataLoaded = false;
    vm.servers = [];

    GlancesBrowser.init();

    $scope.$on('servers_list_refreshed', function (event, data) {
        vm.servers = data;
        vm.dataLoaded = true;
    });

    vm.openServer = function(server) {
        $window.open('http://' + server.key, '_blank');
    }
}
