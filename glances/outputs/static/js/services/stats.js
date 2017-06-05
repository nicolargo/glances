glancesApp.service('GlancesStats', function($http, $q, GlancesPluginHelper, CONFIG, ARGUMENTS) {

    this.getData = function() {
        return $q.all([
            this.getAllStats(),
            this.getAllViews()
        ]).then(function(results) {
            return {
                'stats': results[0],
                'views': results[1],
                'isBsd': results[0]['system']['os_name'] === 'FreeBSD',
                'isLinux': results[0]['system']['os_name'] === 'Linux',
                'isMac': results[0]['system']['os_name'] === 'Darwin',
                'isWindows': results[0]['system']['os_name'] === 'Windows'
            };
        });
    };

    this.getAllStats = function() {
        return $http.get('api/2/all').then(function (response) {
            return response.data;
        });
    };

    this.getAllViews = function() {
        return $http.get('api/2/all/views').then(function (response) {
            return response.data;
        });
    };

    this.getHelp = function() {
        return $http.get('api/2/help').then(function (response) {
            return response.data;
        });
    };

    // load limits to init GlancePlugin helper
    $http.get('api/2/all/limits').then(function (response) {
      GlancesPluginHelper.setLimits(response.data);
    });
    $http.get('api/2/config').then(function (response) {
        angular.extend(CONFIG, response.data);
    });
    $http.get('api/2/args').then(function (response) {
        angular.extend(ARGUMENTS, response.data);
    });

});
