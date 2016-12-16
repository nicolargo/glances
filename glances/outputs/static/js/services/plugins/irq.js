glancesApp.service('GlancesPluginIrq', function() {
    var _pluginName = "irq";
    this.irqs = [];

    this.setData = function(data, views) {
        data = data[_pluginName];
        this.irqs = [];

        for (var i = 0; i < data.length; i++) {
            var IrqData = data[i];
            var timeSinceUpdate = IrqData['time_since_update'];

            var irq = {
                'irq_line': IrqData['irq_line'],
                'irq_rate': IrqData['irq_rate']
            };

            this.irqs.push(irq);
        }
    };
});
