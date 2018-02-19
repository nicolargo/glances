
export default function GlancesPluginAlertController($scope, favicoService) {
    var vm = this;
    var _alerts = [];

    $scope.$on('data_refreshed', function (event, data) {
        var alertStats = data.stats['alert'];
        if (!_.isArray(alertStats)) {
            alertStats = [];
        }

        _alerts = [];
        for (var i = 0; i < alertStats.length; i++) {
            var alertalertStats = alertStats[i];
            var alert = {};

            alert.name = alertalertStats[3];
            alert.level = alertalertStats[2];
            alert.begin = alertalertStats[0] * 1000;
            alert.end = alertalertStats[1] * 1000;
            alert.ongoing = alertalertStats[1] == -1;
            alert.min = alertalertStats[6];
            alert.mean = alertalertStats[5];
            alert.max = alertalertStats[4];

            if (!alert.ongoing) {
                var duration = alert.end - alert.begin;
                var seconds = parseInt((duration / 1000) % 60)
                    , minutes = parseInt((duration / (1000 * 60)) % 60)
                    , hours = parseInt((duration / (1000 * 60 * 60)) % 24);

                alert.duration = _.padStart(hours, 2, '0') + ":" + _.padStart(minutes, 2, '0') + ":" + _.padStart(seconds, 2, '0');
            }

            _alerts.push(alert);
        }

        if (vm.hasOngoingAlerts()) {
            favicoService.badge(vm.countOngoingAlerts());
        } else {
            favicoService.reset();
        }
    });

    vm.hasAlerts = function () {
        return _alerts.length > 0;
    };

    vm.getAlerts = function () {
        return _alerts;
    };

    vm.count = function () {
        return _alerts.length;
    };

    vm.hasOngoingAlerts = function () {
        return _.filter(_alerts, {'ongoing': true}).length > 0;
    };

    vm.countOngoingAlerts = function () {
        return _.filter(_alerts, {'ongoing': true}).length;
    }
}
