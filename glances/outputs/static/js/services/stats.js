glancesApp.service('GlancesStats', function($http, $q, GlancesPluginHelper) {

    var _config;

    this.getData = function() {
        return $q.all([
            this.getAllStats(),
            this.getAllViews()
        ]).then(function(results) {
            return {
                'stats': results[0],
                'view': results[1]
            };
        });
    };

    this.getAllStats = function() {
        return $http.get('/api/2/all').then(function (response) {
            return response.data;
        });
    };

    this.getAllLimits = function() {
        return $http.get('/api/2/all/limits').then(function (response) {
            return response.data;
        });
    };

    this.getAllViews = function() {
        return $http.get('/api/2/all/views').then(function (response) {
            return response.data;
        });
    };

    this.getHelp = function() {
        return $http.get('/api/2/help').then(function (response) {
            return response.data;
        });
    };

    this.getConfig = function() {
        if (!_config) {
            return $http.get('/api/2/config').then(function (response) {
                _config = response.data;

                return response.data;
            });
        }

        var deferrer = $q.defer();
        deferrer.resolve(_config);

        return deferrer.promise;
    };

    this.getArguments = function() {
        return $http.get('/api/2/args').then(function (response) {
            return response.data;
        });
    };

    // load limits to init GlancePlugin helper
    this.getAllLimits().then(function(limits) {
        GlancesPluginHelper.setLimits(limits);
    });

});