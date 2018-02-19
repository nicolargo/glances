
export default function GlancesPluginQuicklookController($scope, GlancesStats, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;
    var _view = {};

    vm.mem = null;
    vm.cpu = null;
    vm.cpu_name = null;
    vm.cpu_hz_current = null;
    vm.cpu_hz = null;
    vm.swap = null;
    vm.percpus = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['quicklook'];
        _view = data.views['quicklook'];

        vm.mem = stats.mem;
        vm.cpu = stats.cpu;
        vm.cpu_name = stats.cpu_name;
        vm.cpu_hz_current = stats.cpu_hz_current;
        vm.cpu_hz = stats.cpu_hz;
        vm.swap = stats.swap;
        vm.percpus = [];

        angular.forEach(stats.percpu, function (cpu) {
            vm.percpus.push({
                'number': cpu.cpu_number,
                'total': cpu.total
            });
        }, this);
    };

    vm.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
