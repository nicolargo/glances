glancesApp.service('GlancesPluginRaid', function () {
    var _pluginName = "raid";
    this.disks = [];

    this.setData = function (data, views) {
      this.disks = [];
        data = data[_pluginName];

        _.forIn(data, function(diskData, diskKey) {
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

            _.forEach(diskData.components, function(number, name) {
                disk.components.push({
                    'number': number,
                    'name': name
                });
            });

            this.disks.push(disk);
        }, this);
    };

    this.hasDisks = function() {
        return this.disks.length > 0;
    }

    this.getAlert = function(disk) {
        if (disk.inactive) {
            return 'critical';
        }

        if (disk.degraded) {
            return 'warning';
        }

        return 'ok'
    }
});
