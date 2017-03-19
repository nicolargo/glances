'use strict';

function GlancesPluginCloudController() {
    var vm = this;

    vm.provider = null;
    vm.instance = null;

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['cloud'];

        if (data['ami-id'] !== undefined) {
            vm.provider = 'AWS EC2';
            vm.instance =  data['instance-type'] + ' instance ' + data['instance-id'] + ' (' + data['region'] + ')';
        }
    };
}
