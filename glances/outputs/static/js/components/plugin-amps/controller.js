
export default function GlancesPluginAmpsController($scope, GlancesStats, favicoService) {
    var vm = this;
    vm.processes = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var processes = data.stats['amps'];

        vm.processes = [];
        angular.forEach(processes, function (process) {
            if (process.result !== null) {
                vm.processes.push(process);
            }
        }, this);
    };

    vm.getDescriptionDecoration = function (process) {
        var count = process.count;
        var countMin = process.countmin;
        var countMax = process.countmax;
        var decoration = "ok";

        if (count > 0) {
            if ((countMin === null || count >= countMin) && (countMax === null || count <= countMax)) {
                decoration = 'ok';
            } else {
                decoration = 'careful';
            }
        } else {
            decoration = countMin === null ? 'ok' : 'critical';
        }

        return decoration;
    }
}
