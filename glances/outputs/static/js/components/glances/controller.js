'use strict';

function GlancesController($timeout, GlancesStats, REFRESH_TIME, Hotkeys) {
    var vm = this;

    vm.dataLoaded = false;
    vm.stats = {};

    var refreshDataSuccess = function (data) {
        data.isBsd = data.stats['system']['os_name'] === 'FreeBSD';
        data.isLinux = data.stats['system']['os_name'] === 'Linux';
        data.isMac = data.stats['system']['os_name'] === 'Darwin';
        data.isWindows = data.stats['system']['os_name'] === 'Windows';

        vm.stats = data;
        vm.is_disconnected = false;
        vm.dataLoaded = true;

        data = undefined;
        nextLoad();
    };

    var refreshDataError = function() {
        vm.is_disconnected = true;
        nextLoad();
    };

    vm.refreshData = function () {
        GlancesStats.getData().then(refreshDataSuccess, refreshDataError);
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
