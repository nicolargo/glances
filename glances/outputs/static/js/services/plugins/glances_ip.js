glancesApp.service('GlancesPluginIp', function() {
    var _pluginName = "ip";

    this.address  = null;
    this.gateway = null;
    this.mask = null;
    this.maskCidr = null;

    this.setData = function(data, views) {
        data = data[_pluginName];

        this.address = data['address'];
        this.gateway = data['gateway'];
        this.mask = data['mask'];
        this.maskCidr = data['mask_cidr'];
    };
});
