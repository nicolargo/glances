'use strict';

function GlancesPluginWifiController($filter) {
    var vm = this;
    var _view = {};

    vm.hotspots = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['wifi'];
        _view = stats.view['wifi'];

        vm.hotspots = [];
        for (var i = 0; i < data.length; i++) {
            var hotspotData = data[i];

            if (hotspotData['ssid'] === '') {
                continue;
            }

            vm.hotspots.push({
                'ssid': hotspotData['ssid'],
                'encrypted': hotspotData['encrypted'],
                'signal': hotspotData['signal'],
                'encryption_type': hotspotData['encryption_type']
            });
        }

        vm.hotspots = $filter('orderBy')(vm.hotspots, 'ssid');

        data = undefined;
    };

    vm.getDecoration = function(hotpost, field) {
        if(_view[hotpost.ssid][field] == undefined) {
            return;
        }

        return _view[hotpost.ssid][field].decoration.toLowerCase();
    };
}
