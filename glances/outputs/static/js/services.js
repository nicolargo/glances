import { store } from './store.js';
import Favico from 'favico.js';

// prettier-ignore
const fetchAll = () => fetch('api/4/all', { method: 'GET' }).then((response) => response.json());
// prettier-ignore
const fetchAllViews = () => fetch('api/4/all/views', { method: 'GET' }).then((response) => response.json());
// prettier-ignore
const fetchAllLimits = () => fetch('api/4/all/limits', { method: 'GET' }).then((response) => response.json());
// prettier-ignore
const fetchArgs = () => fetch('api/4/args', { method: 'GET' }).then((response) => response.json());
// prettier-ignore
const fetchConfig = () => fetch('api/4/config', { method: 'GET' }).then((response) => response.json());


class GlancesHelperService {
    limits = {};
    limitSuffix = ['critical', 'careful', 'warning'];

    setLimits(limits) {
        this.limits = limits;
    }

    getLimit(pluginName, limitName) {
        if (this.limits[pluginName] != undefined) {
            if (this.limits[pluginName][limitName] != undefined) {
                return this.limits[pluginName][limitName]
            }
        }
        return null
    }

    getAlert(pluginName, limitNamePrefix, current, maximum, log) {
        current = current || 0;
        maximum = maximum || 100;
        log = log || false;

        var log_str = log ? '_log' : '';
        var value = (current * 100) / maximum;

        if (this.limits[pluginName] != undefined) {
            for (var i = 0; i < this.limitSuffix.length; i++) {
                var limitName = limitNamePrefix + this.limitSuffix[i];
                var limit = this.limits[pluginName][limitName];
                if (value >= limit) {
                    var pos = limitName.lastIndexOf('_');
                    var className = limitName.substring(pos + 1);
                    return className + log_str;
                }
            }
        }

        return 'ok' + log_str;
    }

    getAlertLog(pluginName, limitNamePrefix, current, maximum) {
        return this.getAlert(pluginName, limitNamePrefix, current, maximum, true);
    }
}

export const GlancesHelper = new GlancesHelperService();

class GlancesStatsService {
    data = undefined;

    init(REFRESH_TIME = 60) {
        let timeout = undefined;
        const fetchData = () => {
            store.status = 'PENDING';
            return Promise.all([fetchAll(), fetchAllViews()])
                .then((response) => {
                    const data = {
                        stats: response[0],
                        views: response[1],
                        isBsd: response[0]['system']['os_name'] === 'FreeBSD',
                        isLinux: response[0]['system']['os_name'] === 'Linux',
                        isSunOS: response[0]['system']['os_name'] === 'SunOS',
                        isMac: response[0]['system']['os_name'] === 'Darwin',
                        isWindows: response[0]['system']['os_name'] === 'Windows'
                    };
                    this.data = data;
                    store.data = data;
                    store.status = 'SUCCESS';
                })
                .catch((error) => {
                    console.log(error);
                    store.status = 'FAILURE';
                })
                .then(() => {
                    if (timeout) {
                        clearTimeout(timeout);
                    }
                    timeout = setTimeout(fetchData, REFRESH_TIME * 1000); // in milliseconds
                });
        };
        fetchData();

        fetchAllLimits().then((response) => {
            GlancesHelper.setLimits(response);
        });

        fetchArgs().then((response = {}) => {
            store.args = { ...store.args, ...response };
        });

        fetchConfig().then((response = {}) => {
            store.config = { ...store.config, ...response };
        });
    }

    getData() {
        return this.data;
    }
}

export const GlancesStats = new GlancesStatsService();

class GlancesFavicoService {
    constructor() {
        this.favico = new Favico({
            animation: 'none'
        });
    }
    badge(nb) {
        this.favico.badge(nb);
    }
    reset() {
        this.favico.reset();
    }
}

export const GlancesFavico = new GlancesFavicoService();
