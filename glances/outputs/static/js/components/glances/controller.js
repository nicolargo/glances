'use strict';

function GlancesController($interval, GlancesStats) {
    var vm = this;

    vm.dataLoaded = false;
    vm.stats = {};
    vm.refreshData = function () {
        GlancesStats.getData().then(function (data) {

            data.isBsd = data.stats['system']['os_name'] === 'FreeBSD';
            data.isLinux = data.stats['system']['os_name'] === 'Linux';
            data.isMac = data.stats['system']['os_name'] === 'Darwin';
            data.isWindows = data.stats['system']['os_name'] === 'Windows';

            vm.stats = data;
            vm.is_disconnected = false;
            vm.dataLoaded = true;
        }, function() {
            vm.is_disconnected = true;
        });
    };

    vm.refreshData();
    var refreshTime = 5; // arguments.time
    $interval(function () {
        vm.refreshData();
    }, refreshTime * 1000); // in milliseconds
}
