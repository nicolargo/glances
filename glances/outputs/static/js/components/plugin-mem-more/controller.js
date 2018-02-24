
export default function GlancesPluginMemMoreController($scope, GlancesStats) {
    var vm = this;

    vm.active = null;
    vm.inactive = null;
    vm.buffers = null;
    vm.cached = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['mem'];

        vm.active = stats['active'];
        vm.inactive = stats['inactive'];
        vm.buffers = stats['buffers'];
        vm.cached = stats['cached'];
    }
}
