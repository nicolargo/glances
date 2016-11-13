glancesApp.service('GlancesPluginSystem', function() {
    var _pluginName = "system";

    this.hostname  = null;
    this.platform = null;
    this.humanReadableName = null;
    this.os = {
        'name': null,
        'version': null
    };

    this.setData = function(data, views) {
        data = data[_pluginName];
        
        this.hostname = data['hostname'];
        this.platform = data['platform'];
        this.os.name = data['os_name'];
        this.os.version = data['os_version'];
        this.humanReadableName = data['hr_name'];
    };

    this.isBsd = function() {
        return this.os.name === 'FreeBSD';
    };

    this.isLinux = function() {
        return this.os.name === 'Linux';
    };

    this.isMac = function() {
        return this.os.name === 'Darwin';
    };

    this.isWindows = function() {
        return this.os.name === 'Windows';
    };
});
