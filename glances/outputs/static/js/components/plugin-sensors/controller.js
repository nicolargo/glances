
export default function GlancesPluginSensorsController($scope, GlancesStats, GlancesPluginHelper, ARGUMENTS) {
    var vm = this;
    vm.sensors = [];
    var convertToFahrenheit = ARGUMENTS.fahrenheit;

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

        _.forEach(stats, function (sensor) {
            if (convertToFahrenheit && sensor.type != 'battery' && sensor.type != 'fan_speed') {
                sensor.value = parseFloat(sensor.value * 1.8 + 32).toFixed(1);
                sensor.unit = 'F';
            }
        });

        vm.sensors = stats;
    };

    vm.getAlert = function (sensor) {
        var current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;

        return GlancesPluginHelper.getAlert('sensors', 'sensors_' + sensor.type + '_', current);
    };
}
