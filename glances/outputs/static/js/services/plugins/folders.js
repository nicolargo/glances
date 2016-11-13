glancesApp.service('GlancesPluginFolders', function() {
    var _pluginName = "folders";
    this.folders = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.folders = [];

        for (var i = 0; i < data.length; i++) {
            var folderData = data[i];

            var folder = {
                'path': folderData['path'],
                'size': folderData['size'],
                'careful': folderData['careful'],
                'warning': folderData['warning'],
                'critical': folderData['critical']
            };

            this.folders.push(folder);
        }
    };

    this.getDecoration = function(folder) {

        if (!Number.isInteger(folder.size)) {
            return;
        }

        if (folder.critical !== null && folder.size > (folder.critical * 1000000)) {
            return 'critical';
        } else if (folder.warning !== null && folder.size > (folder.warning * 1000000)) {
            return 'warning';
        } else if (folder.careful !== null && folder.size > (folder.careful * 1000000)) {
            return 'careful';
        }

        return 'ok';
    };
});
