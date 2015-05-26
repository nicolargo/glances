glancesApp.controller('statsController', function($scope, $http, $interval, $q, $routeParams, $filter) {

    $scope.limitSuffix = ['critical', 'careful', 'warning'];
    $scope.refreshTime = 3;
    $scope.pluginLimits = [];
    $scope.sorter = {
        column: "cpu_percent",
        auto: true,
        isReverseColumn: function(column) {
            return !(column == 'username' || column == 'name');
        },
        getColumnLabel: function(column) {
            if (_.isEqual(column, ['io_read', 'io_write'])) {
                return 'io_counters';
            } else {
                return column;
            }
        }
    };
    $scope.help_screen = false;
    $scope.show = {
        'diskio' : true,
        'network' : true,
        'fs' : true,
        'sensors' : true,
        'sidebar' : true,
        'alert' : true,
        'short_process_name': true,
        'per_cpu': false,
        'warning_alerts':true,
        'warning_critical_alerts':true,
        'process_stats':true,
        'top_extended_stats':true,
        'docker_stats':true,
        'network_io_combination':false,
        'network_io_cumulative':false,
        'filesystem_freespace':false,
        'network_by_bytes':true
    };

    $scope.init_refresh_time = function() {
        if ($routeParams != undefined && $routeParams.refresh_time != undefined) {
            var new_refresh_time = parseInt($routeParams.refresh_time)
            if (new_refresh_time >= 1) {
                $scope.refreshTime = new_refresh_time
            }
        }
    }

    $scope.init_limits = function() {
      $http.get('/api/2/all/limits').success(function(response, status, headers, config) {
          $scope.pluginLimits = response
      }).error(function(response, status, headers, config) {
          console.log('error : ' + response+ status + headers + config);
      });
    }

    $scope.init_help = function() {
        $http.get('/api/2/help').success(function(response, status, headers, config) {
            $scope.help = response
        });
    }

    $scope.show_hide = function(bloc) {
        if(bloc == 'help') {
            $scope.help_screen = !$scope.help_screen
        } else {
            $scope.show[bloc] = !$scope.show[bloc]
        }
    }

    var canceler = undefined;

    /**
     * Refresh all the data of the view
     */
    $scope.refreshData = function() {
        canceler = $q.defer();
        $http.get('/api/2/all', {timeout: canceler.promise}).success(function(response, status, headers, config) {

            function timemillis(array) {
                var sum = 0.0
                for (var i = 0; i < array.length; i++) {
                    sum += array[i] * 1000.0;
                }
                return sum;
            }
            function timedelta(input) {
                var sum = timemillis(input);
                var d = new Date(sum);

                return {
                  hours: d.getUTCHours(), // TODO : multiple days ( * (d.getDay() * 24)))
                  minutes: d.getUTCMinutes(),
                  seconds: d.getUTCSeconds(),
                  milliseconds: parseInt("" + d.getUTCMilliseconds() / 10)
                };
            };

            function durationBetweenTwoDates(startDate, endDate) {
              var duration = endDate - startDate;
              var seconds = parseInt((duration/1000)%60)
                  , minutes = parseInt((duration/(1000*60))%60)
                  , hours = parseInt((duration/(1000*60*60))%24);

              return _.padLeft(hours,2,'0') + ":" + _.padLeft(minutes,2,'0') + ":" + _.padLeft(seconds,2,'0');
            }

            for (var i = 0; i < response['processlist'].length; i++) {
                var process = response['processlist'][i]
                process.memvirt = process.memory_info[1]
                process.memres  = process.memory_info[0]
                process.timeplus = timedelta(process.cpu_times)
                process.timemillis = timemillis(process.cpu_times)

                process.io_read = '?';
                process.io_write = '?';

                if (process.io_counters) {
                  process.io_read  = (process.io_counters[0] - process.io_counters[2]) / process.time_since_update;

                  if (process.io_read != 0) {
                    process.io_read = $filter('bytes')(process.io_read);
                  }

                  process.io_write = (process.io_counters[1] - process.io_counters[3]) / process.time_since_update;

                  if (process.io_write != 0) {
                    process.io_write = $filter('bytes')(process.io_write);
                  }
                }
            }
            for (var i = 0; i < response['alert'].length; i++) {
                var alert = response['alert'][i];
                alert.begin = alert[0] * 1000;
                alert.end = alert[1] * 1000;
                alert.ongoing = alert[1] == -1;

                if (!alert.ongoing) {
                  alert.duration = durationBetweenTwoDates(alert.begin, alert.end);
                }
            }

            _.remove(response['sensors'], function(sensor) {
              return sensor.type == "battery" && _.isArray(sensor.value) && _.isEmpty(sensor.value);
            });

            $scope.is_bsd = response['system'].os_name === 'FreeBSD';
            $scope.is_linux = response['system'].os_name === 'Linux';
            $scope.is_mac = response['system'].os_name === 'Darwin';
            $scope.is_windows = response['system'].os_name === 'Windows';

            $scope.result = response;
            canceler.resolve()
        }).error(function(d, status, headers, config) {
            console.log('error status:' + status + " - headers = " + headers);
            canceler.resolve()
        });
    }

    $scope.isNice = function(nice) {
      if(nice !== undefined && (($scope.is_windows && nice != 32) || (!$scope.is_windows && nice != 0))) {
        return true;
      }

      return false;
    }

    $scope.getAlert = function(pluginName, limitNamePrefix, current, maximum, log) {
      current = current || 0;
      maximum = maximum || 100;
      log = log || false;
      log_str = log ? '_log' : '';

      var value = (current * 100) / maximum;

      if ($scope.pluginLimits != undefined && $scope.pluginLimits[pluginName] != undefined) {
          for (var i = 0; i < $scope.limitSuffix.length; i++) {
              var limitName = limitNamePrefix + $scope.limitSuffix[i]
              var limit = $scope.pluginLimits[pluginName][limitName]

              if (value >= limit) {
                  var pos = limitName.lastIndexOf("_")
                  var className = limitName.substring(pos + 1)

                  return className + log_str;
              }
          }
      }

      return "ok" + log_str;
    }

    $scope.getAlertLog = function(pluginName, limitNamePrefix, current, maximum) {
      return $scope.getAlert(pluginName, limitNamePrefix, current, maximum, true);
    }

    $scope.init_refresh_time();
    $scope.init_limits();
    $scope.init_help();

    var stop;
    $scope.configure_refresh = function () {
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
                $scope.stop_refresh();
                $scope.configure_refresh();
            }
    );

    $scope.stop_refresh = function() {
        if (angular.isDefined(stop)) {
            $interval.cancel(stop);
            stop = undefined;
        }
    };

    $scope.$on('$destroy', function() {
        // Make sure that the interval is destroyed too
        $scope.stop_refresh();
    });

    $scope.onKeyDown = function($event) {
        if ($event.keyCode == keycodes.a) { // a  Sort processes automatically
            $scope.sorter.column = "cpu_percent";
            $scope.sorter.auto = true;
        } else if ($event.keyCode == keycodes.c) {//c  Sort processes by CPU%
            $scope.sorter.column =  "cpu_percent";
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.m) {//m  Sort processes by MEM%
            $scope.sorter.column = "memory_percent";
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.p) {//p  Sort processes by name
            $scope.sorter.column = "name";
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.i) {//i  Sort processes by I/O rate
            $scope.sorter.column = ['io_read', 'io_write'];
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.t) {//t  Sort processes by CPU times
            $scope.sorter.column = "timemillis";
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.u) {//t  Sort processes by user
            $scope.sorter.column = "username";
            $scope.sorter.auto = false;
        } else if ($event.keyCode == keycodes.d) {//d  Show/hide disk I/O stats
            $scope.show_hide('diskio')
        } else if ($event.keyCode == keycodes.f) {//f  Show/hide filesystem stats
            $scope.show_hide('fs')
        } else if ($event.keyCode == keycodes.n) {//n sort_by Show/hide network stats
            $scope.show_hide('network')
        } else if ($event.keyCode == keycodes.s) {//s  Show/hide sensors stats
            $scope.show_hide('sensors')
        } else if ($event.keyCode == keycodes.TWO && $event.shiftKey) {//2  Show/hide left sidebar
            $scope.show_hide('sidebar')
        } else if ($event.keyCode == keycodes.z) {//z  Enable/disable processes stats
            $scope.show_hide('process_stats')
        } else if ($event.keyCode == keycodes.e) {//e  Enable/disable top extended stats
            $scope.show_hide('top_extended_stats')
        } else if ($event.keyCode == keycodes.SLASH) {// SLASH  Enable/disable short processes name
            $scope.show_hide('short_process_name')
        } else if ($event.keyCode == keycodes.D && $event.shiftKey) {//D  Enable/disable Docker stats
            $scope.show_hide('docker_stats')
        } else if ($event.keyCode == keycodes.b) {//b  Bytes or bits for network I/O
            $scope.show_hide('network_by_bytes')
        } else if ($event.keyCode == keycodes.l) {//l  Show/hide alert logs
            $scope.show_hide('alert')
        } else if ($event.keyCode == keycodes.w) {//w  Delete warning alerts
            $scope.show_hide('warning_alerts')
        } else if ($event.keyCode == keycodes.x) {//x  Delete warning and critical alerts
            $scope.show_hide('warning_critical_alerts')
        } else if ($event.keyCode == keycodes.ONE && $event.shiftKey) {//1  Global CPU or per-CPU stats
            $scope.show_hide('per_cpu')
        } else if ($event.keyCode == keycodes.h) {//h  Show/hide this help screen
            $scope.show_hide('help')
        } else if ($event.keyCode == keycodes.T && $event.shiftKey) {//T  View network I/O as combination
            $scope.show_hide('network_io_combination')
        } else if ($event.keyCode == keycodes.u) {//u  View cumulative network I/O
            $scope.show_hide('network_io_cumulative')
        } else if ($event.keyCode == keycodes.F && $event.shiftKey) {//F  Show filesystem free space
            $scope.show_hide('filesystem_freespace')
        } else if ($event.keyCode == keycodes.g) {//g  Generate graphs for current history
            // not available
        } else if ($event.keyCode == keycodes.r) {//r  Reset history
            // not available
        } else if ($event.keyCode == keycodes.q) {//q  Quit (Esc and Ctrl-C also work)
            // not available
        }
    }
});
