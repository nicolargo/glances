
export default function GlancesPluginProcesscountController($scope, GlancesStats) {
    var vm = this;

    vm.total = null;
    vm.running = null;
    vm.sleeping = null;
    vm.stopped = null;
    vm.thread = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var processcountStats = data.stats['processcount'];

        vm.total = processcountStats['total'] || 0;
        vm.running = processcountStats['running'] || 0;
        vm.sleeping = processcountStats['sleeping'] || 0;
        vm.stopped = processcountStats['stopped'] || 0;
        vm.thread = processcountStats['thread'] || 0;
    }
}
