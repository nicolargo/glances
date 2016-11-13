glancesApp.service('GlancesPluginLoad', function() {
    var _pluginName = "load";
    var _view = {};

    this.cpucore = null;
    this.min1 = null;
    this.min5 = null;
    this.min15 = null;

    this.setData = function(data, views) {
        _view = views[_pluginName];
        data = data[_pluginName];

        this.cpucore = data['cpucore'];
        this.min1 = data['min1'];
        this.min5 = data['min5'];
        this.min15 = data['min15'];
    };

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
});
