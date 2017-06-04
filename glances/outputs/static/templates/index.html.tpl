<!DOCTYPE html>
<html ng-app="glancesApp">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title ng-bind="title">Glances</title>

    <link rel="icon" type="image/x-icon" href="favicon.ico" />
    <link rel="stylesheet" type="text/css" href="css/normalize.min.css" />
    <link rel="stylesheet" type="text/css" href="css/bootstrap.min.css" />
    <link rel="stylesheet" type="text/css" href="css/style.min.css" />

    <script type="text/javascript" src="js/vendor.min.js"></script>
    <script>
        angular
            .module('glances.config', [])
            .constant('REFRESH_TIME', {{ refresh_time }});
    </script>
    <script type="text/javascript" src="js/main.min.js"></script>
    <script type="text/javascript" src="js/templates.min.js"></script>
</head>

<body>
  <glances></glances>
</body>
</html>
