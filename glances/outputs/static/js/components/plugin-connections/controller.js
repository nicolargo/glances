
export default function GlancesPluginConnectionsController($scope, GlancesStats) {
    var vm = this;
    var _view = {};

    vm.listen = null;
    vm.initiated = null;
    vm.established = null;
    vm.terminated = null;
    vm.tracked = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['connections'];
        _view = data.views['connections'];

        vm.listen = stats['LISTEN'];
        vm.initiated = stats['initiated'];
        vm.established = stats['ESTABLISHED'];
        vm.terminated = stats['terminated'];
        vm.tracked = {
            count: stats['nf_conntrack_count'],
            max: stats['nf_conntrack_max'],
        };
    };

    vm.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
