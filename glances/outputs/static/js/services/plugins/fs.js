glancesApp.service('GlancesPluginFs', function() {
    var _pluginName = "fs";
    var _view = {};
    this.fileSystems = [];

    this.setData = function(data, views) {
        _view = views[_pluginName];
        data = data[_pluginName];
        this.fileSystems = [];

        for (var i = 0; i < data.length; i++) {
            var fsData = data[i];

            var shortMountPoint = fsData['mnt_point'];
            if (shortMountPoint.length > 9) {
              shortMountPoint = '_' + fsData['mnt_point'].slice(-8);
            }

            var fs = {
                'name': fsData['device_name'],
                'mountPoint': fsData['mnt_point'],
                'shortMountPoint': shortMountPoint,
                'percent': fsData['percent'],
                'size': fsData['size'],
                'used': fsData['used'],
                'free': fsData['free']
            };

            this.fileSystems.push(fs);
        }
    };

    this.getDecoration = function(mountPoint, field) {
        if(_view[mountPoint][field] == undefined) {
            return;
        }

        return _view[mountPoint][field].decoration.toLowerCase();
    };
});
