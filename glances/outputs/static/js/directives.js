
import angular from "angular";

export default angular.module("glancesApp").directive("sortableTh", function () {
    return {
        restrict: 'A',
        scope: {
            sorter: '='
        },
        link: function (scope, element, attrs) {

            element.addClass('sortable');

            scope.$watch(function () {
                return scope.sorter.column;
            }, function (newValue, oldValue) {

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

            element.on('click', function () {

                scope.sorter.column = attrs.column;

                scope.$apply();
            });
        }
    };
});