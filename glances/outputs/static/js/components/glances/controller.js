'use strict';

function GlancesController($scope, $rootScope, $timeout, GlancesStats, REFRESH_TIME, Hotkeys, ARGUMENTS) {
    var vm = this;
    vm.dataLoaded = false;
    vm.arguments = ARGUMENTS;

    vm.refreshData = function () {
        GlancesStats.getData().then(function (data) {
            $rootScope.title = data.stats.system.hostname + ' - Glances';
            $scope.$broadcast('data_refreshed', data);
            vm.dataLoaded = true;

            nextLoad();
        }, function() {
            $scope.$broadcast('is_disconnected');
            nextLoad();
        });
    };

    var loadPromise;
    var cancelNextLoad = function() {
      $timeout.cancel(loadPromise);
    };

    var nextLoad = function() {
      cancelNextLoad();
      loadPromise = $timeout(vm.refreshData, REFRESH_TIME * 1000); // in milliseconds
    };

    vm.refreshData();

    Hotkeys.registerHotkey(Hotkeys.createHotkey({
        key: 'm',
        callback: function () {
          console.log('Sort processes by MEM%');
        }
    }));
}
