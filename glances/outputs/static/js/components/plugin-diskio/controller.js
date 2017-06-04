'use strict';

function GlancesPluginDiskioController($scope, $filter) {
    var vm = this;

    vm.disks = [];

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['diskio'];
      stats = $filter('orderBy')(stats,'disk_name');

      vm.disks = [];
      for (var i = 0; i < stats.length; i++) {
          var diskioData = stats[i];
          var timeSinceUpdate = diskioData['time_since_update'];

          vm.disks.push({
              'name': diskioData['disk_name'],
              'bitrate': {
                  'txps': $filter('bytes')(diskioData['read_bytes'] / timeSinceUpdate),
                  'rxps': $filter('bytes')(diskioData['write_bytes'] / timeSinceUpdate)
              },
              'count': {
                  'txps': $filter('bytes')(diskioData['read_count'] / timeSinceUpdate),
                  'rxps': $filter('bytes')(diskioData['write_count'] / timeSinceUpdate)
              },
              'alias': diskioData['alias'] !== undefined ? diskioData['alias'] : null
          });
      }
    });
}
