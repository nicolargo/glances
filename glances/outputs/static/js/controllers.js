var glancesApp = angular.module('glancesApp', []);

glancesApp.filter('min_size', function() {
	return function(input) {
		var max = 8;
		if (input.length > max) {
			return "_" + input.substring(input.length - max)
		}
		return input
	};
});
glancesApp.filter('exclamation', function() {
	return function(input) {
		if (input == undefined || input =='') {
			return '?'
		}
		return input
	};
});

/** 
 * Fork from https://gist.github.com/thomseddon/3511330 
 * &nbsp; => \u00A0
 * WARNING : kilobyte (kB) != kibibyte (KiB) (more info here : http://en.wikipedia.org/wiki/Byte )
 **/
glancesApp.filter('bytes', function() {
	return function(bytes, precision) {
		if (isNaN(parseFloat(bytes)) || !isFinite(bytes) || bytes == 0) return '0B';
		var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'],
			number = Math.floor(Math.log(bytes) / Math.log(1000));
		return (bytes / Math.pow(1000, Math.floor(number))).toFixed(precision) + units[number];
	}
});

glancesApp.controller('bodyController', [ '$scope', '$http', '$interval', '$q', function($scope, $http, $interval, $q) {

	$scope.limitSuffix = ['critical', 'careful', 'warning']
	$scope.refreshTime = 3
	$scope.pluginLimits = []
	
	$scope.initLimits = function() {
		$scope.pluginsList();
	}
	
	$scope.pluginsList = function() {
		$http.get('/api/2/pluginslist').success(function(d, status, headers, config) {
			$scope.plugins = d;
			
			for (var i = 0;i< $scope.plugins.length; i++) {
				var pluginName = $scope.plugins[i];
				$scope.limits(pluginName);
			}
			
		}).error(function(d, status, headers, config) {
			console.log('error' + d + status + headers + config);
		});
	}
	$scope.limits = function(pluginName) {
		url = "/api/2/" + pluginName + "/limits"
		console.log("url = " + url)
		$http.get(url).success(function(d, status, headers, config) {
			$scope.pluginLimits[pluginName] = d;
		}).error(function(d, status, headers, config) {
			console.log('error');
		});
	}
	
	var canceler = undefined;
	
	/**
	 * Refresh all the data of the view
	 */
	$scope.refreshData = function() {
		canceler = $q.defer();
		$http.get('/api/2/all', {timeout: canceler.promise}).success(function(response, status, headers, config) {
			//alert('success');
			
			function timemillis(array) {
				var sum = 0.0
				for (var i = 0; i < array.length; i++) {
					sum += array[i] * 1000.0;
				}
				return sum;
			}
			function leftpad(input) {
				if (input < 10) {
					return "0" + input
				}
				return input
			}
			function timedelta(input) {
				var sum = timemillis(input);
				var d = new Date(sum);
				var hour = leftpad(d.getUTCHours()) // TODO : multiple days ( * (d.getDay() * 24)))
				var minutes = leftpad(d.getUTCMinutes())
				var seconds = leftpad(d.getUTCSeconds())
				var milliseconds = parseInt("" + d.getUTCMilliseconds() / 10)
				var millisecondsStr = leftpad(milliseconds)
				return hour +":" + minutes + ":" + seconds + "." + millisecondsStr
			};
		
			for (var i = 0; i < response['processlist'].length; i++) {
				var process = response['processlist'][i]
				process.memvirt = process.memory_info[1]
				process.memres  = process.memory_info[0]
				process.timeformatted = timedelta(process.cpu_times)
				process.timemillis = timemillis(process.cpu_times)
				process.io_read  = (process.io_counters[0] - process.io_counters[2]) / process.time_since_update
				process.io_write = (process.io_counters[1] - process.io_counters[3]) / process.time_since_update
			}
			$scope.result = response;
			canceler.resolve()
		}).error(function(d, status, headers, config) {
			console.log('error status:' + status + " - headers = " + headers);
			canceler.resolve()
		});
	}
		
	$scope.getClass = function(pluginName, limitNamePrefix, value, num) {
		if ($scope.pluginLimits != undefined && $scope.pluginLimits[pluginName] != undefined) {
			for (var i = 0; i < $scope.limitSuffix.length; i++) {
				var limitName = limitNamePrefix + $scope.limitSuffix[i]
				var limit = $scope.pluginLimits[pluginName][limitName]
				
				if (value > limit) {
					//console.log("value = " + value + " - limit = " + limit)
					var pos = limitName.lastIndexOf("_")
					var className = limitName.substring(pos + 1)
					//console.log("className = " + className)
					if (num == 1) {
						return className + '_log'
					}
					return className
				}
			}
		}
		if (num == 1) {
			return "ok_log"
		}
		return "ok";
	}
    
    $scope.initLimits();
    
    var stop;
    $scope.configureRefresh = function () {
    	if (!angular.isDefined(stop)) {
    		//$scope.refreshData();
		    stop = $interval(function() {
		    	$scope.refreshData();
		    }, $scope.refreshTime * 1000); // in milliseconds
    	}
    }
    
    $scope.$watch(
    		function() { return $scope.refreshTime; },
    		function(newValue, oldValue) {
    			$scope.stopRefresh();
    			$scope.configureRefresh();
    		}
    );

    $scope.stopRefresh = function() {
    	if (angular.isDefined(stop)) {
    		$interval.cancel(stop);
    		stop = undefined;
    	}
    };
      
    $scope.$on('$destroy', function() {
    	// Make sure that the interval is destroyed too
    	$scope.stopRefresh();
    });
	
} ]);