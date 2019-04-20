
export default function GlancesPluginSystemController($scope, GlancesStats) {
    var vm = this;

    vm.hostname = null;
    vm.platform = null;
    vm.humanReadableName = null;
    vm.os = {
        'name': null,
        'version': null
    };

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    $scope.$on('is_disconnected', function () {
        vm.isDisconnected = true;
    });

    var loadData = function (data) {
        var stats = data.stats['system'];

        vm.isLinux = data.isLinux;
        vm.hostname = stats['hostname'];
        vm.platform = stats['platform'];
        vm.os.name = stats['os_name'];
        vm.os.version = stats['os_version'];
        vm.humanReadableName = stats['hr_name'];
        vm.isDisconnected = false;
    }
}
