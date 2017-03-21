'use strict';

function GlancesPluginDiskioController($filter) {
    var vm = this;

    vm.disks = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['diskio'];

        data = $filter('orderBy')(data,'disk_name');

        vm.disks = [];
        for (var i = 0; i < data.length; i++) {
            var diskioData = data[i];
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

        data = undefined;
    };
}
