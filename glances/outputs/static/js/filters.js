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
    return function (bytes, precision) {
        if (isNaN(parseFloat(bytes)) || !isFinite(bytes) || bytes == 0){
            return '0B';
        }
        var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'],
        number = Math.floor(Math.log(bytes) / Math.log(1000));
        return (bytes / Math.pow(1000, Math.floor(number))).toFixed(precision) + units[number];
    }
});

glancesApp.filter('bits', function() {
    return function (bits, precision) {
        if (isNaN(parseFloat(bits)) || !isFinite(bits) || bits == 0){
            return '0b';
        }
        var units = ['b', 'kb', 'Mb', 'Gb', 'Tb', 'Pb'],
        number = Math.floor(Math.log(bits) / Math.log(1000));
        return (bits / Math.pow(1000, Math.floor(number))).toFixed(precision) + units[number];
    }
});
