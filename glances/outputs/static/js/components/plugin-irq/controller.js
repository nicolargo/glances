
export default function GlancesPluginIrqController($scope, GlancesStats) {
    var vm = this;
    vm.irqs = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
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
    }
}
