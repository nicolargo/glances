'use strict';

function GlancesPluginLoadController() {
    var vm = this;
    var _view = {};

    vm.cpucore = null;
    vm.min1 = null;
    vm.min5 = null;
    vm.min15 = null;

    vm.$onChanges = function (changes) {
      var stats = changes.stats.currentValue;
      if (stats === undefined || stats.stats === undefined) {
        return;
      }

      var data = stats.stats['load'];
      _view = stats.view['load'];

      vm.cpucore = data['cpucore'];
      vm.min1 = data['min1'];
      vm.min5 = data['min5'];
      vm.min15 = data['min15'];

        data = undefined;
    };

    this.getDecoration = function(value) {
    if(_view[value] === undefined) {
        return;
    }

    return _view[value].decoration.toLowerCase();
};
}
