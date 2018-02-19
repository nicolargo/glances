
export default function GlancesPluginFsController($scope, $filter, GlancesStats, ARGUMENTS) {
    var vm = this;
    var _view = {};
    vm.arguments = ARGUMENTS;
    vm.fileSystems = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['fs'];
        _view = data.views['fs'];

        vm.fileSystems = [];
        for (var i = 0; i < stats.length; i++) {
            var fsData = stats[i];

            var shortMountPoint = fsData['mnt_point'];
            if (shortMountPoint.length > 9) {
                shortMountPoint = '_' + fsData['mnt_point'].slice(-8);
            }

            vm.fileSystems.push({
                'name': fsData['device_name'],
                'mountPoint': fsData['mnt_point'],
                'shortMountPoint': shortMountPoint,
                'percent': fsData['percent'],
                'size': fsData['size'],
                'used': fsData['used'],
                'free': fsData['free']
            });
        }

        vm.fileSystems = $filter('orderBy')(vm.fileSystems, 'mnt_point');
    };

    vm.getDecoration = function (mountPoint, field) {
        if (_view[mountPoint][field] == undefined) {
            return;
        }

        return _view[mountPoint][field].decoration.toLowerCase();
    };
}
