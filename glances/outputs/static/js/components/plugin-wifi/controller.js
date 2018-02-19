
export default function GlancesPluginWifiController($scope, $filter, GlancesStats) {
    var vm = this;
    var _view = {};

    vm.hotspots = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['wifi'];
        _view = data.views['wifi'];
        //stats = [{"ssid": "Freebox-40A258", "encrypted": true, "signal": -45, "key": "ssid", "encryption_type": "wpa2", "quality": "65/70"}];

        vm.hotspots = [];
        for (var i = 0; i < stats.length; i++) {
            var hotspotData = stats[i];

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
    };

    vm.getDecoration = function (hotpost, field) {
        if (_view[hotpost.ssid][field] === undefined) {
            return;
        }

        return _view[hotpost.ssid][field].decoration.toLowerCase();
    };
}
