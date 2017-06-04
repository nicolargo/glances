'use strict';

function GlancesPluginLoadController($scope) {
    var vm = this;
    var _view = {};

    vm.cpucore = null;
    vm.min1 = null;
    vm.min5 = null;
    vm.min15 = null;

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['load'];
      _view = data.view['load'];

      vm.cpucore = stats['cpucore'];
      vm.min1 = stats['min1'];
      vm.min5 = stats['min5'];
      vm.min15 = stats['min15'];
    });

    this.getDecoration = function(value) {
    if(_view[value] === undefined) {
        return;
    }

    return _view[value].decoration.toLowerCase();
};
}
