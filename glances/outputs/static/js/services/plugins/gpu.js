glancesApp.service('GlancesPluginGpu', function() {
    var _pluginName = "gpu";
    var _view = {};
    this.gpus = [];
    this.name = "GPU";

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        data = [{"key": "gpu_id", "mem": 48.64645, "proc": 60.73, "gpu_id": 0, "name": "GeForce GTX 560 Ti"},
            {"key": "gpu_id", "mem": 70.743, "proc": 80.28, "gpu_id": 1, "name": "GeForce GTX 560 Ti"},
            {"key": "gpu_id", "mem": 0, "proc": 0, "gpu_id": 2, "name": "GeForce GTX 560 Ti"}];
        _view = {"0": {"mem": {"decoration": "DEFAULT"}, "proc": {"decoration": "CAREFUL"}}};

        if (data.length === 0) {
            return;
        }

        this.gpus = [];
        this.name = "GPU";
        var sameName = true;

        for (var i = 0; i < data.length; i++) {
            var gpuData = data[i];

            var gpu = gpuData;

            this.gpus.push(gpu);
        }

        if (data.length === 1 ) {
            this.name = data[0].name;
        } else if (sameName) {
            this.name = data.length + ' GPU ' + data[0].name;
        }
    };

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
});
