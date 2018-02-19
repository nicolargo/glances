
export default function GlancesPluginNetworkController($scope, $filter, GlancesStats, ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;
    vm.networks = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var networkStats = data.stats['network'];

        vm.networks = [];
        for (var i = 0; i < networkStats.length; i++) {
            var networkData = networkStats[i];

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
    }
}
