'use strict';

function GlancesPluginMemswapController($scope) {
    var vm = this;
    var _view = {};

    vm.percent = null;
    vm.total = null;
    vm.used = null;
    vm.free = null;

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['memswap'];
      _view = data.views['memswap'];

      vm.percent = stats['percent'];
      vm.total = stats['total'];
      vm.used = stats['used'];
      vm.free = stats['free'];
    });

    this.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
