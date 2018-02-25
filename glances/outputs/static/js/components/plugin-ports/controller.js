
export default function GlancesPluginPortsController($scope, GlancesStats) {
    var vm = this;
    vm.ports = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['ports'];

        vm.ports = [];
        angular.forEach(stats, function (port) {
            vm.ports.push(port);
        }, this);
    }

    vm.getPortDecoration = function (port) {
        if (port.status === null) {
            return 'careful';
        } else if (port.status === false) {
            return 'critical';
        } else if (port.rtt_warning !== null && port.status > port.rtt_warning) {
            return 'warning';
        }

        return 'ok';
    };

    vm.getWebDecoration = function (web) {
        var okCodes = [200, 301, 302];

        if (web.status === null) {
            return 'careful';
        } else if (okCodes.indexOf(web.status) === -1) {
            return 'critical';
        } else if (web.rtt_warning !== null && web.elapsed > web.rtt_warning) {
            return 'warning';
        }

        return 'ok';
    };
}
