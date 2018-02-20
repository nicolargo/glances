
export default function GlancesPluginFoldersController($scope, GlancesStats) {
    var vm = this;
    vm.folders = [];

    vm.$onInit = function () {
        loadData(GlancesStats.getData());
    };

    $scope.$on('data_refreshed', function (event, data) {
        loadData(data);
    });

    var loadData = function (data) {
        var stats = data.stats['folders'];
        vm.folders = [];

        for (var i = 0; i < stats.length; i++) {
            var folderData = stats[i];

            var folder = {
                'path': folderData['path'],
                'size': folderData['size'],
                'careful': folderData['careful'],
                'warning': folderData['warning'],
                'critical': folderData['critical']
            };

            vm.folders.push(folder);
        }
    }

    vm.getDecoration = function (folder) {

        if (!Number.isInteger(folder.size)) {
            return;
        }

        if (folder.critical !== null && folder.size > (folder.critical * 1000000)) {
            return 'critical';
        } else if (folder.warning !== null && folder.size > (folder.warning * 1000000)) {
            return 'warning';
        } else if (folder.careful !== null && folder.size > (folder.careful * 1000000)) {
            return 'careful';
        }

        return 'ok';
    };
}
