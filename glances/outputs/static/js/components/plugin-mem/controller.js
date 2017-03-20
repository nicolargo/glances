'use strict';

function GlancesPluginMemController() {
    var vm = this;
    var _view = {};

    vm.percent = null;
    vm.total = null;
    vm.used = null;
    vm.free = null;

    vm.$onChanges = function (changes) {
        var stats = changes.stats.currentValue;
        if (stats === undefined || stats.stats === undefined) {
            return;
        }

        var data = stats.stats['mem'];
        _view = stats.view['mem'];

        vm.percent = data['percent'];
        vm.total = data['total'];
        vm.used = data['used'];
        vm.free = data['free'];
    };

    this.getDecoration = function (value) {
        if (_view[value] === undefined) {
            return;
        }

        return _view[value].decoration.toLowerCase();
    };
}
