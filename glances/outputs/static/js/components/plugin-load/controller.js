
export default function GlancesPluginLoadController($scope, GlancesStats) {
    var vm = this;
    var _view = {};

    vm.cpucore = null;
    vm.min1 = null;
    vm.min5 = null;
    vm.min15 = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['load'];
        _view = data.views['load'];

        vm.cpucore = stats['cpucore'];
        vm.min1 = stats['min1'];
        vm.min5 = stats['min5'];
        vm.min15 = stats['min15'];
    };

    vm.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
