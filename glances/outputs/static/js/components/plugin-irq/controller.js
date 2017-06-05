'use strict';

function GlancesPluginIrqController($scope) {
    var vm = this;
    vm.irqs = [];

    $scope.$on('data_refreshed', function(event, data) {
      var stats = data.stats['irq'];
      vm.irqs = [];

      for (var i = 0; i < stats.length; i++) {
          var IrqData = stats[i];

          var irq = {
              'irq_line': IrqData['irq_line'],
              'irq_rate': IrqData['irq_rate']
          };

          vm.irqs.push(irq);
      }
    });
}
