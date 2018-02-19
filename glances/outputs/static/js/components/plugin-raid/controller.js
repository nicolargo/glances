
export default function GlancesPluginRaidController($scope, GlancesStats) {
    var vm = this;
    vm.disks = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var disks = [];
        var stats = data.stats['raid'];

        _.forIn(stats, function (diskData, diskKey) {
            var disk = {
                'name': diskKey,
                'type': diskData.type == null ? 'UNKNOWN' : diskData.type,
                'used': diskData.used,
                'available': diskData.available,
                'status': diskData.status,
                'degraded': diskData.used < diskData.available,
                'config': diskData.config == null ? '' : diskData.config.replace('_', 'A'),
                'inactive': diskData.status == 'inactive',
                'components': []
            };

            _.forEach(diskData.components, function (number, name) {
                disk.components.push({
                    'number': number,
                    'name': name
                });
            });

            disks.push(disk);
        });

        vm.disks = disks;
    };

    vm.hasDisks = function () {
        return vm.disks.length > 0;
    };

    vm.getAlert = function (disk) {
        if (disk.inactive) {
            return 'critical';
        }

        if (disk.degraded) {
            return 'warning';
        }

        return 'ok'
    };
}
