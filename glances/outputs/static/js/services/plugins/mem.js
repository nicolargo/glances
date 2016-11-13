glancesApp.service('GlancesPluginMem', function() {
    var _pluginName = "mem";
    var _view = {};

    this.percent = null;
    this.total = null;
    this.used = null;
    this.free = null;
    this.version = null;
    this.active = null;
    this.inactive = null;
    this.buffers = null;
    this.cached = null;

    this.setData = function(data, views) {
        _view = views[_pluginName];
        data = data[_pluginName];

        this.percent = data['percent'];
        this.total = data['total'];
        this.used = data['used'];
        this.free = data['free'];
        this.active = data['active'];
        this.inactive = data['inactive'];
        this.buffers = data['buffers'];
        this.cached = data['cached'];
    };

    this.getDecoration = function(value) {
        if(_view[value] == undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
});
