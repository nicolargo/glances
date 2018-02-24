
export default function GlancesPluginCloudController($scope, GlancesStats) {
    var vm = this;

    vm.provider = null;
    vm.instance = null;

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['cloud'];

        if (stats['ami-id'] !== undefined) {
            vm.provider = 'AWS EC2';
            vm.instance = stats['instance-type'] + ' instance ' + stats['instance-id'] + ' (' + stats['region'] + ')';
        }
    }
}
