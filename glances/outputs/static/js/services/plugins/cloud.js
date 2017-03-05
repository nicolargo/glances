glancesApp.service('GlancesPluginCloud', function() {
    var _pluginName = "cloud";
    var _provider = null;
    var _instance = null;

    this.setData = function(data, views) {
        data = data[_pluginName];

        if (data['ami-id'] !== undefined) {
          _provider = 'AWS EC2';
          _instance =  data['instance-type'] + ' instance ' + data['instance-id'] + ' (' + data['region'] + ')';
        }
    }

    this.getProvider = function() {
      return _provider;
    }

    this.getInstance = function() {
      return _instance;
    }
});
