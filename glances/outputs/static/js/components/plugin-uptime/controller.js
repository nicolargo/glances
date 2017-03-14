'use strict';

function GlancesPluginUptimeController() {
    var vm = this;

    this.value = null

    vm.$onChanges = function (changes) {
      var stats = changes.stats.currentValue;
      if (stats === undefined || stats.stats === undefined) {
        return;
      }

      vm.value = stats.stats['uptime'];
    };
}
