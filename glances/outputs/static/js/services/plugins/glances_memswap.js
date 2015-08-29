glancesApp.service('GlancesPluginMemSwap', function() {
    var _pluginName = "memswap";
    var _view = {};

    this.percent = null;
    this.total = null;
    this.used = null;
    this.free = null;

    this.setData = function(data, views) {
        _view = views[_pluginName];
        data = data[_pluginName];

        this.percent = data['percent'];
        this.total = data['total'];
        this.used = data['used'];
        this.free = data['free'];
    };

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
});
