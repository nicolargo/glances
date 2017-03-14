'use strict';

function GlancesPluginSystemController() {
    var vm = this;
    var _pluginName = "system";

    vm.hostname  = null;
    vm.platform = null;
    vm.humanReadableName = null;
    vm.os = {
        'name': null,
        'version': null
    };

    vm.$onChanges = function (changes) {
      var stats = changes.stats.currentValue;
      if (stats === undefined || stats.stats === undefined) {
        return;
      }

      var data = stats.stats[_pluginName];

      vm.hostname = data['hostname'];
      vm.platform = data['platform'];
      vm.os.name = data['os_name'];
      vm.os.version = data['os_version'];
      vm.humanReadableName = data['hr_name'];
    };

    vm.isBsd = function() {
        return this.os.name === 'FreeBSD';
    };

    vm.isLinux = function() {
        return this.os.name === 'Linux';
    };

    vm.isMac = function() {
        return this.os.name === 'Darwin';
    };

    vm.isWindows = function() {
        return this.os.name === 'Windows';
    };
}
