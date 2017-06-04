'use strict';

function GlancesPluginProcessController(ARGUMENTS) {
    var vm = this;
    vm.arguments = ARGUMENTS;

    vm.sorter = {
        column: "cpu_percent",
        auto: true,
        isReverseColumn: function (column) {
            return !(column === 'username' || column === 'name');
        },
        getColumnLabel: function (column) {
            if (_.isEqual(column, ['io_read', 'io_write'])) {
                return 'io_counters';
            } else {
                return column;
            }
        }
    };
}
