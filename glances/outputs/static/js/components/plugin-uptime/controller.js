
export default function GlancesPluginUptimeController($scope, GlancesStats) {
    var vm = this;
    vm.value = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        vm.value = data.stats['uptime'];
    }
}
