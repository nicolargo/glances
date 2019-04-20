<!DOCTYPE html>
<html ng-app="glancesApp">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title ng-bind="title">Glances</title>

    <link rel="icon" type="image/x-icon" href="favicon.ico" />
    <script type="text/javascript" src="glances.js"></script>
</head>

<body>
  <glances refresh-time="{{ refresh_time }}"></glances>
</body>
</html>
