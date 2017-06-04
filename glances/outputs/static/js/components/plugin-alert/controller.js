'use strict';

function GlancesPluginAmpsController($scope, favicoService) {
    var vm = this;
    vm.processes = [];

    $scope.$on('alertStats_refreshed', function(event, data) {
      var processes = data.stats['amps'];

      this.processes = [];
      angular.forEach(processes, function(process) {
          if (process.result !== null) {
              this.processes.push(process);
          }
      }, this);
    });

    vm.getDescriptionDecoration = function(process) {
        var count = process.count;
        var countMin = process.countmin;
        var countMax = process.countmax;
        var decoration = "ok";

        if (count > 0) {
            if ((countMin == null || count >= countMin) && (countMax == null || count <= countMax)) {
                decoration = 'ok';
            } else {
                decoration = 'careful';
            }
        } else {
            decoration = countMin == null ? 'ok' : 'critical';
        }

        return decoration;
    }
}
