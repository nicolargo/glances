glancesApp.service('GlancesPluginDiskio', function() {
    var _pluginName = "diskio";
    this.disks = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.disks = [];

        for (var i = 0; i < data.length; i++) {
            var diskioData = data[i];

            var diskio = {
                'name': diskioData['disk_name'],
                'readBytes': diskioData['read_bytes'],
                'writeBytes': diskioData['write_bytes']
            };

            this.disks.push(diskio);
        }
    };
});
