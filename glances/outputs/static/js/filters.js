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
        if (input === undefined || input === '') {
            return '?';
        }
        return input;
    };
});

glancesApp.filter('bytes', function() {
    return function (bytes, low_precision) {
        low_precision = low_precision || false;
        if (isNaN(parseFloat(bytes)) || !isFinite(bytes) || bytes == 0){
            return '0';
        }

        var symbols = ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];
        var prefix = {
          'Y': 1208925819614629174706176,
          'Z': 1180591620717411303424,
          'E': 1152921504606846976,
          'P': 1125899906842624,
          'T': 1099511627776,
          'G': 1073741824,
          'M': 1048576,
          'K': 1024
        };

        var reverseSymbols = _(symbols).reverse().value();
        for (var i = 0; i < reverseSymbols.length; i++) {
          var symbol = reverseSymbols[i];
          var value = bytes / prefix[symbol];

          if(value > 1) {
            var decimal_precision = 0;

            if(value < 10) {
              decimal_precision = 2;
            }
            else if(value < 100) {
              decimal_precision = 1;
            }

            if(low_precision) {
              if(symbol == 'MK') {
                decimal_precision = 0;
              }
              else {
                decimal_precision = _.min([1, decimal_precision]);
              }
            }
            else if(symbol == 'K') {
              decimal_precision = 0;
            }

            return parseFloat(value).toFixed(decimal_precision) + symbol;
          }
        }

        return bytes;
    }
});

glancesApp.filter('bits', function($filter) {
    return function (bits, low_precision) {
      bits = Math.round(bits) * 8;
      return $filter('bytes')(bits, low_precision) + 'b';
    }
});

glancesApp.filter('leftPad', function($filter) {
    return function (value, length, chars) {
      length = length || 0;
      chars = chars || ' ';
      return _.padLeft(value, length, chars);
    }
});
