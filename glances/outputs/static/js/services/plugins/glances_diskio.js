glancesApp.service('GlancesPluginDiskio', function($filter) {
    var _pluginName = "diskio";
    this.disks = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        data = $filter('orderBy')(data,'disk_name');
        this.disks = [];

        for (var i = 0; i < data.length; i++) {
            var diskioData = data[i];
            var timeSinceUpdate = diskioData['time_since_update'];

            var diskio = {
                'name': diskioData['disk_name'],
                'bitrate': {
                  'txps': $filter('bytes')(diskioData['read_bytes'] / timeSinceUpdate),
                  'rxps': $filter('bytes')(diskioData['write_bytes'] / timeSinceUpdate)
                },
                'count': {
                  'txps': $filter('bytes')(diskioData['read_count'] / timeSinceUpdate),
                  'rxps': $filter('bytes')(diskioData['write_count'] / timeSinceUpdate)
                }
            };

            this.disks.push(diskio);
        }
    };
});
