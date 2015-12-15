glancesApp.service('GlancesPluginAlert', function () {
    var _pluginName = "alert";
    var _alerts = [];

    this.setData = function (data, views) {
        data = data[_pluginName];
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

                alert.duration = _.padLeft(hours, 2, '0') + ":" + _.padLeft(minutes, 2, '0') + ":" + _.padLeft(seconds, 2, '0');
            }

            _alerts.push(alert);
        }
    };

    this.hasAlerts = function () {
        return _alerts.length > 0;
    };

    this.getAlerts = function () {
        return _alerts;
    };

    this.count = function () {
        return _alerts.length;
    };
});
