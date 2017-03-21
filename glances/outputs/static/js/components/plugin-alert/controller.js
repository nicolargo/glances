'use strict';

function GlancesPluginAlertController(favicoService) {
    var vm = this;
    var _alerts = [];

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['alert'];
        _alerts = [];

        if(!_.isArray(data)) {
            data = [];
        }

        for (var i = 0; i < data.length; i++) {
            var alertData = data[i];
            var alert = {};

            alert.name = alertData[3];
            alert.level = alertData[2];
            alert.begin = alertData[0] * 1000;
            alert.end = alertData[1] * 1000;
            alert.ongoing = alertData[1] == -1;
            alert.min = alertData[6];
            alert.mean = alertData[5];
            alert.max = alertData[4];

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

        data = undefined;
    };

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
        return _.filter(_alerts, { 'ongoing': true }).length > 0;
    };

    vm.countOngoingAlerts = function () {
        return _.filter(_alerts, { 'ongoing': true }).length;
    }
}
