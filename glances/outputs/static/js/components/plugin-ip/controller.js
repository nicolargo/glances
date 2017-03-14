'use strict';

function GlancesPluginIpController() {
    var vm = this;

    this.address  = null;
    this.gateway = null;
    this.mask = null;
    this.maskCidr = null;
    this.publicAddress = null;

    vm.$onChanges = function (changes) {
      var stats = changes.stats.currentValue;
      if (stats === undefined || stats.stats === undefined) {
        return;
      }

      var data = stats.stats['ip'];

      vm.address = data.address;
      vm.gateway = data.gateway;
      vm.mask = data.mask;
      vm.maskCidr = data.mask_cidr;
      vm.publicAddress = data.public_address
    };
}
