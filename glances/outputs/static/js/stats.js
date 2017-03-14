glancesApp.service('GlancesStats', function($http, $q) {
    var _stats = [], _views = [], _limits = [], _config = {};

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
            _stats = response.data;

            return response.data;
        });
    };

    this.getAllLimits = function() {
        return $http.get('/api/2/all/limits').then(function (response) {
            _limits = response.data;

            return response.data;
        });
    };

    this.getAllViews = function() {
        return $http.get('/api/2/all/views').then(function (response) {
            _views = response.data;

            return response.data;
        });
    };

    this.getHelp = function() {
        return $http.get('/api/2/help').then(function (response) {
            return response.data;
        });
    };

    this.getConfig = function() {
        return $http.get('/api/2/config').then(function (response) {
            _config = response.data;

            return _config;
        });
    };

    this.getArguments = function() {
        return $http.get('/api/2/args').then(function (response) {
            return response.data;
        });
    };

});
