'use strict';

function GlancesPluginFsController($filter) {
    var vm = this;
    var _view = {};

    vm.fileSystems = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['fs'];
        _view = stats.view['fs'];

        vm.fileSystems = [];
        for (var i = 0; i < data.length; i++) {
            var fsData = data[i];

            var shortMountPoint = fsData['mnt_point'];
            if (shortMountPoint.length > 9) {
                shortMountPoint = '_' + fsData['mnt_point'].slice(-8);
            }

            vm.fileSystems.push(fs = {
                'name': fsData['device_name'],
                'mountPoint': fsData['mnt_point'],
                'shortMountPoint': shortMountPoint,
                'percent': fsData['percent'],
                'size': fsData['size'],
                'used': fsData['used'],
                'free': fsData['free']
            });
        }

        vm.fileSystems = $filter('orderBy')(vm.fileSystems,'mnt_point');

        data = undefined;
    };

    vm.getDecoration = function(mountPoint, field) {
        if(_view[mountPoint][field] == undefined) {
            return;
        }

        return _view[mountPoint][field].decoration.toLowerCase();
    };
}
