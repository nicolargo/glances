glancesApp.service('GlancesPluginDocker', function(GlancesPlugin) {

    var _pluginName = "docker";
    this.containers = [];
    this.version = null;

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.containers = [];

        if(_.isEmpty(data)) {
            return;
        }

        for (var i = 0; i < data['containers'].length; i++) {
            var containerData = data['containers'][i];

            var container = {
                'id': containerData.Id,
                'name': containerData.Names[0],
                'status': containerData.Status,
                'cpu': containerData.cpu.total,
                'memory': containerData.memory.total != undefined ? containerData.memory.total : '?',
                'command': containerData.Command,
                'image': containerData.Image
            };

            this.containers.push(container);
        }

        this.version = data['version']['Version'];
    };
});
