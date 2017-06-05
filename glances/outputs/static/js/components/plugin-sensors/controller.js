'use strict';

function GlancesPluginSensorsController($scope, GlancesStats, GlancesPluginHelper) {
    var vm = this;
    vm.sensors = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['sensors'];

        _.remove(stats, function (sensor) {
            return (_.isArray(sensor.value) && _.isEmpty(sensor.value)) || sensor.value === 0;
        });

        vm.sensors = data;
    };

    vm.getAlert = function (sensor) {
        var current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;

        return GlancesPluginHelper.getAlert('sensors', 'sensors_' + sensor.type + '_', current);
    };
}
