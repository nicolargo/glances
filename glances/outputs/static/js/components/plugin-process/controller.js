
export default function GlancesPluginProcessController(ARGUMENTS, hotkeys) {
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

    // a => Sort processes automatically
    hotkeys.add({
        combo: 'a',
        callback: function () {
            vm.sorter.column = "cpu_percent";
            vm.sorter.auto = true;
        }
    });

    // c => Sort processes by CPU%
    hotkeys.add({
        combo: 'c',
        callback: function () {
            vm.sorter.column = "cpu_percent";
            vm.sorter.auto = false;
        }
    });

    // m => Sort processes by MEM%
    hotkeys.add({
        combo: 'm',
        callback: function () {
            vm.sorter.column = "memory_percent";
            vm.sorter.auto = false;
        }
    });

    // u => Sort processes by user
    hotkeys.add({
        combo: 'u',
        callback: function () {
            vm.sorter.column = "username";
            vm.sorter.auto = false;
        }
    });

    // p => Sort processes by name
    hotkeys.add({
        combo: 'p',
        callback: function () {
            vm.sorter.column = "name";
            vm.sorter.auto = false;
        }
    });

    // i => Sort processes by I/O rate
    hotkeys.add({
        combo: 'i',
        callback: function () {
            vm.sorter.column = ['io_read', 'io_write'];
            vm.sorter.auto = false;
        }
    });

    // t => Sort processes by time
    hotkeys.add({
        combo: 't',
        callback: function () {
            vm.sorter.column = "timemillis";
            vm.sorter.auto = false;
        }
    });
}
