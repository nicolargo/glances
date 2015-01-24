<!DOCTYPE HTML>
<html>
    <head>
        <meta http-equiv="refresh" content="{{refresh_time}}">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Glances</title>
        <link rel="icon" type="image/x-icon" href="favicon.ico" />
        <link rel="stylesheet" type="text/css" href="normalize.css" />
        <link rel="stylesheet" type="text/css" href="bootstrap.min.css" />
        <link rel="stylesheet" type="text/css" href="style.css" />
        <script src="modernizr.custom.js"></script>
    </head>
    <body>
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-12">
                    <div class="pull-left">
                        % include('plugin_text', plugin_name="system", stats=stats['system'])
                    </div>
                    <div class="pull-right">
                        % include('plugin_text', plugin_name="uptime", stats=stats['uptime'])
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-3">
                    % include('plugin_table', plugin_name="cpu", stats=stats['cpu'])    
                </div>
                <div class="col-sm-3 col-lg-2 col-lg-offset-1">
                    % include('plugin_table', plugin_name="load", stats=stats['load'])
                </div>
                <div class="col-sm-3 col-lg-3">
                    % include('plugin_table', plugin_name="mem", stats=stats['mem'])
                </div>
                <div class="col-sm-3 col-lg-2 col-lg-offset-1">
                    % include('plugin_table', plugin_name="memswap", stats=stats['memswap'])
                </div>
            </div>
            <div class="row">
                <div class="col-sm-3">
                    % include('plugin_table', plugin_name="network", stats=stats['network'])
                    % include('plugin_table', plugin_name="diskio", stats=stats['diskio'])
                    % include('plugin_table', plugin_name="fs", stats=stats['fs'])
                    % include('plugin_table', plugin_name="sensors", stats=stats['sensors'])
                </div>
                <div class="col-sm-9">
                    % include('plugin_table', plugin_name="alert", stats=stats['alert'])
                    % include('plugin_text', plugin_name="processcount", stats=stats['processcount'])
                    % include('plugin_table', plugin_name="docker", stats=stats['docker'])
                    <div class="row">
                        <div class="col-sm-9">
                            % include('plugin_table', plugin_name="monitor", stats=stats['monitor'])        
                        </div>
                    </div>
                    % include('plugin_table', plugin_name="processlist", stats=stats['processlist'])
                </div>
            </div>
        </div>
    </body>
</html>