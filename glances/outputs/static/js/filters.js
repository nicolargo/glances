import { min } from 'lodash';
import sanitizeHtml from 'sanitize-html';

export function bits(bits, low_precision) {
    bits = Math.round(bits) * 8;
    return bytes(bits, low_precision) + 'b';
}

export function bytes(bytes, low_precision) {
    low_precision = low_precision || false;
    if (isNaN(parseFloat(bytes)) || !isFinite(bytes) || bytes == 0) {
        return bytes;
    }

    const symbols = ['Y', 'Z', 'E', 'P', 'T', 'G', 'M', 'K'];
    const prefix = {
        Y: 1208925819614629174706176,
        Z: 1180591620717411303424,
        E: 1152921504606846976,
        P: 1125899906842624,
        T: 1099511627776,
        G: 1073741824,
        M: 1048576,
        K: 1024
    };

    for (var i = 0; i < symbols.length; i++) {
        var symbol = symbols[i];
        var value = bytes / prefix[symbol];

        if (value > 1) {
            var decimal_precision = 0;

            if (value < 10) {
                decimal_precision = 2;
            } else if (value < 100) {
                decimal_precision = 1;
            }

            if (low_precision) {
                if (symbol == 'MK') {
                    decimal_precision = 0;
                } else {
                    decimal_precision = min([1, decimal_precision]);
                }
            } else if (symbol == 'K') {
                decimal_precision = 0;
            }

            return parseFloat(value).toFixed(decimal_precision) + symbol;
        }
    }

    return bytes.toFixed(0);
}

export function exclamation(input) {
    if (input === undefined || input === '') {
        return '?';
    }
    return input;
}

export function leftPad(value, length, chars) {
    length = length || 0;
    chars = chars || ' ';
    return String(value).padStart(length, chars);
}

export function limitTo(value, limit) {
    if (typeof value.slice !== 'function') {
        value = String(value);
    }
    return value.slice(0, limit);
}

export function minSize(input, max, begin = true) {
    max = max || 8;
    if (input.length > max) {
        if (begin) {
            return input.substring(0, max - 1) + '_';
        } else {
            return '_' + input.substring(input.length - max + 1);
        }
    }
    return input;
}

export function nl2br(input) {
    function escapeHTML(html) {
        var div = document.createElement('div');
        div.innerText = html;
        return div.innerHTML;
    }

    if (typeof input === 'undefined') {
        return input;
    }

    var sanitizedInput = escapeHTML(input);
    var html = sanitizedInput.replace(/\n/g, '<br>');

    return sanitizeHtml(html);
}

export function number(value, options) {
    return new Intl.NumberFormat(
        undefined,
        typeof options === 'number' ? { maximumFractionDigits: options } : options
    ).format(value);
}

export function timemillis(array) {
    var sum = 0.0;
    for (var i = 0; i < array.length; i++) {
        sum += array[i] * 1000.0;
    }
    return sum;
}

export function timedelta(value) {
    var sum = timemillis(value);
    var d = new Date(sum);
    var doy = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 1000 / 60 / 60 / 24);
    return {
        hours: d.getUTCHours() + (doy - 1) * 24,
        minutes: d.getUTCMinutes(),
        seconds: d.getUTCSeconds(),
        milliseconds: parseInt('' + d.getUTCMilliseconds() / 10)
    };
}
