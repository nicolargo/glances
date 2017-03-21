'use strict';

function GlancesPluginNetworkController($filter) {
    var vm = this;

    vm.networks = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['network'];

        vm.networks = [];
        for (var i = 0; i < data.length; i++) {
            var networkData = data[i];

            var network = {
                'interfaceName': networkData['interface_name'],
                'rx': networkData['rx'],
                'tx': networkData['tx'],
                'cx': networkData['cx'],
                'time_since_update': networkData['time_since_update'],
                'cumulativeRx': networkData['cumulative_rx'],
                'cumulativeTx': networkData['cumulative_tx'],
                'cumulativeCx': networkData['cumulative_cx']
            };

            vm.networks.push(network);
        }

        vm.networks = $filter('orderBy')(vm.networks, 'interfaceName');

        data = undefined;
    };
}
