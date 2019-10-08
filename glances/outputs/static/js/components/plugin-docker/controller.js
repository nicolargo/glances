
export default function GlancesPluginDockerController($scope, GlancesStats) {
    var vm = this;
    vm.containers = [];
    vm.version = null;

    var loadData = function (data) {
        var stats = data.stats['docker'];
        vm.containers = [];

        if (_.isEmpty(stats) || _.isEmpty(stats['containers']) ) {
            return;
        }

        vm.containers = stats['containers'].map(function(containerData) {
            return {
                'id': containerData.Id,
                'name': containerData.name,
                'status': containerData.Status,
                'cpu': containerData.cpu.total,
                'memory': containerData.memory.usage != undefined ? containerData.memory.usage : '?',
                'ior': containerData.io.ior != undefined ? containerData.io.ior : '?',
                'iow': containerData.io.iow != undefined ? containerData.io.iow : '?',
                'io_time_since_update': containerData.io.time_since_update,
                'rx': containerData.network.rx != undefined ? containerData.network.rx : '?',
                'tx': containerData.network.tx != undefined ? containerData.network.tx : '?',
                'net_time_since_update': containerData.network.time_since_update,
                'command': containerData.Command,
                'image': containerData.Image
            };
        });

        vm.version = stats['version']['Version'];
    }

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });
}
