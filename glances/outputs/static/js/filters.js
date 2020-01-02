
import angular from "angular";
import _ from "lodash";

function minSizeFilter() {
    return function (input, max) {
        var max = max || 8;
        if (input.length > max) {
            return "_" + input.substring(input.length - max + 1)
        }
        return input
    };
}

function exclamationFilter() {
    return function (input) {
        if (input === undefined || input === '') {
            return '?';
        }
        return input;
    };
}

function bytesFilter() {
    return function (bytes, low_precision) {
        low_precision = low_precision || false;
        if (isNaN(parseFloat(bytes)) || !isFinite(bytes) || bytes == 0) {
            return bytes;
        }

        const symbols = ['Y', 'Z', 'E', 'P', 'T', 'G', 'M', 'K'];
        const prefix = {
            'Y': 1208925819614629174706176,
            'Z': 1180591620717411303424,
            'E': 1152921504606846976,
            'P': 1125899906842624,
            'T': 1099511627776,
            'G': 1073741824,
            'M': 1048576,
            'K': 1024
        };

        for (var i = 0; i < symbols.length; i++) {
            var symbol = symbols[i];
            var value = bytes / prefix[symbol];

            if (value > 1) {
                var decimal_precision = 0;

                if (value < 10) {
                    decimal_precision = 2;
                }
                else if (value < 100) {
                    decimal_precision = 1;
                }

                if (low_precision) {
                    if (symbol == 'MK') {
                        decimal_precision = 0;
                    }
                    else {
                        decimal_precision = _.min([1, decimal_precision]);
                    }
                }
                else if (symbol == 'K') {
                    decimal_precision = 0;
                }

                return parseFloat(value).toFixed(decimal_precision) + symbol;
            }
        }

        return bytes.toFixed(0);
    }
}

function bitsFilter($filter) {
    return function (bits, low_precision) {
        bits = Math.round(bits) * 8;
        return $filter('bytes')(bits, low_precision) + 'b';
    }
}

function leftPadFilter() {
    return function (value, length, chars) {
        length = length || 0;
        chars = chars || ' ';
        return _.padStart(value, length, chars);
    }
}

function timemillisFilter() {
    return function (array) {
        var sum = 0.0;
        for (var i = 0; i < array.length; i++) {
            sum += array[i] * 1000.0;
        }
        return sum;
    }
}

function timedeltaFilter($filter) {
    return function (value) {
        var sum = $filter('timemillis')(value);
        var d = new Date(sum);

        return {
            hours: d.getUTCHours(), // TODO : multiple days ( * (d.getDay() * 24)))
            minutes: d.getUTCMinutes(),
            seconds: d.getUTCSeconds(),
            milliseconds: parseInt("" + d.getUTCMilliseconds() / 10)
        };
    }
}

function nl2brFilter($sce) {
    function escapeHTML(html) {
        var div = document.createElement('div');
        div.innerText = html;

        return div.innerHTML;
    }

    return function (input) {
        if (typeof input === 'undefined') {
            return input;
        }

        var sanitizedInput = escapeHTML(input);
        var html = sanitizedInput.replace(/\n/g, '<br>');

        return $sce.trustAsHtml(html);
    };
}

export default angular.module("glancesApp")
    .filter("min_size", minSizeFilter)
    .filter("exclamation", exclamationFilter)
    .filter("bytes", bytesFilter)
    .filter("bits", bitsFilter)
    .filter("leftPad", leftPadFilter)
    .filter("timemillis", timemillisFilter)
    .filter("timedelta", timedeltaFilter)
    .filter("nl2br", nl2brFilter);
