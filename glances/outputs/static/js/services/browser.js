glancesApp.service('GlancesBrowser', function ($http, $rootScope, $timeout, REFRESH_TIME) {
    var _data = false;

    this.getServersList = function () {
        return _data;
    }

    // load servers list and execute auto refresh
    this.init = function () {
        var refreshData = function () {
            return $http.get('api/2/serverslist').then(function (response) {
                _data = response.data;

                $rootScope.$broadcast('servers_list_refreshed', _data);
                nextLoad();
            }, function () {
                nextLoad();
            });
        };

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
});
