glancesApp.service('GlancesPluginPorts', function() {
  var _pluginName = "ports";
  this.ports = [];

  this.setData = function(data, views) {
    var ports = data[_pluginName];
    this.ports = [];

    angular.forEach(ports, function(port) {
      this.ports.push(port);
    }, this);
  };

  this.getDecoration = function(port) {
    if (port.status === null) {
      return 'careful';
    }

    if (port.status === false) {
      return 'critical';
    }

    if (port.rtt_warning !== null && port.status > port.rtt_warning) {
      return 'warning';
    }

    return 'ok';
  };
});
