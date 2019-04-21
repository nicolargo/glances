
import angular from "angular";

function GlancesStats ($http, $q, $rootScope, $timeout, GlancesPluginHelper, CONFIG, ARGUMENTS) {

    var _data = false;

    this.getData = function () {
        return _data;
    }

    // load config/limit/arguments and execute stats/views auto refresh
    this.init = function (REFRESH_TIME) {
        var refreshData = function () {
            return $q.all([
                getAllStats(),
                getAllViews()
            ]).then(function (results) {
                _data = {
                    'stats': results[0],
                    'views': results[1],
                    'isBsd': results[0]['system']['os_name'] === 'FreeBSD',
                    'isLinux': results[0]['system']['os_name'] === 'Linux',
                    'isMac': results[0]['system']['os_name'] === 'Darwin',
                    'isWindows': results[0]['system']['os_name'] === 'Windows'
                };

                $rootScope.$broadcast('data_refreshed', _data);
                nextLoad();
            }, function () {
                $rootScope.$broadcast('is_disconnected');
                nextLoad();
            });
        };

        // load limits to init GlancePlugin helper
        $http.get('api/3/all/limits').then(function (response) {
            GlancesPluginHelper.setLimits(response.data);
        });
        $http.get('api/3/config').then(function (response) {
            angular.extend(CONFIG, response.data);
        });
        $http.get('api/3/args').then(function (response) {
            angular.extend(ARGUMENTS, response.data);
        });

        var loadPromise;
        var cancelNextLoad = function () {
            $timeout.cancel(loadPromise);
        };

        var nextLoad = function () {
            cancelNextLoad();
            loadPromise = $timeout(refreshData, REFRESH_TIME * 1000); // in milliseconds
        };

        refreshData();
    }

    var getAllStats = function () {
        return $http.get('api/3/all').then(function (response) {
            return response.data;
        });
    };

    var getAllViews = function () {
        return $http.get('api/3/all/views').then(function (response) {
            return response.data;
        });
    };
}

export default angular.module("glancesApp").service("GlancesStats", GlancesStats);
