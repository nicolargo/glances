glancesApp.service('GlancesPluginGpu', function() {
    var _pluginName = "gpu";
    var _view = {};
    this.gpus = [];
    this.name = "GPU";
    this.mean = {};

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        if (data.length === 0) {
            return;
        }

        this.gpus = [];
        this.name = "GPU";
        this.mean = {
            proc: null,
            mem: null
        };
        var sameName = true;

        for (var i = 0; i < data.length; i++) {
            var gpuData = data[i];

            var gpu = gpuData;

            this.mean.proc += gpu.proc;
            this.mean.mem += gpu.mem;

            this.gpus.push(gpu);
        }

        if (data.length === 1 ) {
            this.name = data[0].name;
        } else if (sameName) {
            this.name = data.length + ' GPU ' + data[0].name;
        }

        this.mean.proc = this.mean.proc / data.length;
        this.mean.mem = this.mean.mem / data.length;
    };

    this.getDecoration = function(gpuId, value) {
        if(_view[gpuId][value] == undefined) {
            return;
        }

        return _view[gpuId][value].decoration.toLowerCase();
    };

    this.getMeanDecoration = function(value) {
        return this.getDecoration(0, value);
    };
});
