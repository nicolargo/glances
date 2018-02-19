
export default function GlancesPluginMemController($scope, GlancesStats) {
    var vm = this;
    var _view = {};

    vm.percent = null;
    vm.total = null;
    vm.used = null;
    vm.free = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['mem'];
        _view = data.views['mem'];

        vm.percent = stats['percent'];
        vm.total = stats['total'];
        vm.used = stats['used'];
        vm.free = stats['free'];
    }

    vm.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
