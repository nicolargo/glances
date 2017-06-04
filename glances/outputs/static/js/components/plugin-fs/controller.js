'use strict';

function GlancesPluginFsController($scope, $filter, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;
    var _view = {};

    vm.fileSystems = [];

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['fs'];
      _view = data.view['fs'];

      vm.fileSystems = [];
      for (var i = 0; i < stats.length; i++) {
          var fsData = stats[i];

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
    });

    vm.getDecoration = function(mountPoint, field) {
        if(_view[mountPoint][field] == undefined) {
            return;
        }

        return _view[mountPoint][field].decoration.toLowerCase();
    };
}
