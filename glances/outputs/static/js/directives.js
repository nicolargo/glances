glancesApp.directive("sortableTh", function() {
    return {
        restrict: 'A',
        scope: {
            sorter: '='
        },
        link: function (scope, element, attrs) {

            scope.$watch(function() {
                return scope.sorter.column;
            }, function(newValue, oldValue) {

                if (angular.isArray(newValue)) {
                    if (newValue.indexOf(attrs.column) !== -1) {
                        element.addClass('sort');
                    } else {
                        element.removeClass('sort');
                    }
                } else {
                    if (attrs.column === newValue) {
                        element.addClass('sort');
                    } else {
                        element.removeClass('sort');
                    }
                }

            });

            element.on('click', function() {

                scope.sorter.column = attrs.column;

                scope.$apply();
            });
        }
    };
});

glancesApp.directive("glMonitorList", function() {
    return {
        restrict: 'AE',
        scope: {
            processes: '='
        },
        templateUrl: 'plugins/monitor.html',
        controller: function() {

        }
    }
})

glancesApp.directive("glMonitorProcess", function() {
    return {
        restrict: 'AE',
        require: "^glMonitorList",
        templateUrl: 'components/monitor_process.html',
        scope: {
            process: '='
        },
        link: function(scope, element, attrs) {

            count = scope.process.count;
            countMin = scope.process.countmin;
            countMax = scope.process.countmax;

            if (count > 0) {
                if ((countMin == null || count >= countMin) && (countMax == null || count <= countMax)) {
                    scope.descriptionClass = 'ok';
                } else {
                    scope.descriptionClass = 'careful';
                }
            } else {
                scope.descriptionClass = countMin == null ? 'ok' : 'critical';
            }

        }
    }
});
