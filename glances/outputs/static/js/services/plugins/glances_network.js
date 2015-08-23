glancesApp.service('GlancesPluginNetwork', function() {
    var _pluginName = "network";
    this.networks = [];

    this.setData = function(data, views) {
        this.networks = [];

        for (var i = 0; i < data[_pluginName].length; i++) {
            var networkData = data[_pluginName][i];

            var network = {
                'interfaceName': networkData['interface_name'],
                'rx': networkData['rx'],
                'tx': networkData['tx'],
                'cx': networkData['cx'],
                'cumulativeRx': networkData['cumulative_rx'],
                'cumulativeTx': networkData['cumulative_tx'],
                'cumulativeCx': networkData['cumulative_cx']
            };

            this.networks.push(network);
        }
    };
});
