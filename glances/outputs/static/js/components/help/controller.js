'use strict';

function GlancesHelpController(GlancesStats) {
    var vm = this;

    GlancesStats.getHelp().then(function(help) {
        vm.help = help;
    });
}
