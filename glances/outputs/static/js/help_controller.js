
glancesApp.controller('helpController', [ '$scope',  function($scope) {
    $scope.message = 'help window'

    $scope.onKeyDown = function($event) {
        console.log($event)
        if ($event.keyCode == keycodes.h) {//h  Show/hide this help screen
            window.location = "/"
	    }
    }
}]);
