glancesApp.service('GlancesPluginFolders', function() {
    var _pluginName = "folders";
    var _view = {};
    this.folders = [];

    this.setData = function(data, views) {
        _view = views[_pluginName];
        data = data[_pluginName];
        this.folders = [];

        for (var i = 0; i < data.length; i++) {
            var folderData = data[i];

            var folder = {
                'path': folderData['path'],
                'size': folderData['size']
            };

            this.folders.push(folder);
        }
    };

    this.getDecoration = function(mountPoint, field) {
        if(_view[mountPoint][field] == undefined) {
            return;
        }

        return _view[mountPoint][field].decoration.toLowerCase();
    };
});
