glancesApp.service('GlancesPluginWifi', function() {
    var _pluginName = "wifi";
    var _view = {};
    this.hotspots = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        _view = views[_pluginName];

        this.hotspots = [];
        for (var i = 0; i < data.length; i++) {
            var hotspotData = data[i];

            if (hotspotData['ssid'] === '') {
                continue;
            }

            var hotspot = {
                'ssid': hotspotData['ssid'],
                'encrypted': hotspotData['encrypted'],
                'signal': hotspotData['signal'],
                'encryption_type': hotspotData['encryption_type'],
            };

            this.hotspots.push(hotspot);
        }
    };

    this.getDecoration = function(hotpost, field) {
        if(_view[hotpost.ssid][field] == undefined) {
            return;
        }

        return _view[hotpost.ssid][field].decoration.toLowerCase();
    };
});
