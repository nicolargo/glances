glancesApp.service('GlancesPluginDiskio', function() {
    var _pluginName = "diskio";
    this.disks = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.disks = [];

        for (var i = 0; i < data.length; i++) {
            var diskioData = data[i];
            var timeSinceUpdate = diskioData['time_since_update'];

            var diskio = {
                'name': diskioData['disk_name'],
                'bitrate': {
                  'txps': diskioData['read_bytes'] / timeSinceUpdate,
                  'rxps': diskioData['write_bytes'] / timeSinceUpdate
                },
                'count': {
                  'txps': diskioData['read_count'] / timeSinceUpdate,
                  'rxps': diskioData['write_count'] / timeSinceUpdate
                }
            };

            this.disks.push(diskio);
        }
    };
});
