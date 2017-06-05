'use strict';

function GlancesPluginWifiController($scope, $filter) {
    var vm = this;
    var _view = {};

    vm.hotspots = [];

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['wifi'];
      _view = data.views['wifi'];

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
    });

    vm.getDecoration = function(hotpost, field) {
        if(_view[hotpost.ssid][field] == undefined) {
            return;
        }

        return _view[hotpost.ssid][field].decoration.toLowerCase();
    };
}
