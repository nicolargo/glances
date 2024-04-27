<template>
    <div class="plugin">
        <section id="alerts">
            <span class="title" v-if="hasAlerts">
                Warning or critical alerts (last {{ countAlerts }} entries)
            </span>
            <span class="title" v-else>No warning or critical alert detected</span>
        </section>
        <section id="alert">
            <div class="table">
                <div class="table-row" v-for="(alert, alertId) in alerts" :key="alertId">
                    <div class="table-cell text-left">
                        {{ formatDate(alert.begin) }}
                        {{ alert.tz }}
                        ({{ alert.ongoing ? 'ongoing' : alert.duration }}) -
                        <span v-show="!alert.ongoing"> {{ alert.state }} on </span>
                        <span :class="alert.state.toLowerCase()">
                            {{ alert.type }}
                        </span>
                        ({{ $filters.number(alert.max, 1) }})
                        {{ alert.top }}
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<script>
import { padStart } from 'lodash';
import { GlancesFavico } from '../services.js';

export default {
    props: {
        data: {
            type: Object
        }
    },
    computed: {
        stats() {
            return this.data.stats['alert'];
        },
        alerts() {
            return (this.stats || []).map((alertalertStats) => {
                const alert = {};
                var tzoffset = new Date().getTimezoneOffset();
                alert.state = alertalertStats.state;
                alert.type = alertalertStats.type;
                alert.begin = alertalertStats.begin * 1000 - tzoffset * 60 * 1000;
                alert.end = alertalertStats.end * 1000 - tzoffset * 60 * 1000;
                alert.ongoing = alertalertStats.end == -1;
                alert.min = alertalertStats.min;
                alert.avg = alertalertStats.avg;
                alert.max = alertalertStats.max;
                alert.top = alertalertStats.top.join(', ');

                if (!alert.ongoing) {
                    const duration = alert.end - alert.begin;
                    const seconds = parseInt((duration / 1000) % 60),
                        minutes = parseInt((duration / (1000 * 60)) % 60),
                        hours = parseInt((duration / (1000 * 60 * 60)) % 24);

                    alert.duration =
                        padStart(hours, 2, '0') +
                        ':' +
                        padStart(minutes, 2, '0') +
                        ':' +
                        padStart(seconds, 2, '0');
                }

                return alert;
            });
        },
        hasAlerts() {
            return this.countAlerts > 0;
        },
        countAlerts() {
            return this.alerts.length;
        },
        hasOngoingAlerts() {
            return this.countOngoingAlerts > 0;
        },
        countOngoingAlerts() {
            return this.alerts.filter(({ ongoing }) => ongoing).length;
        }
    },
    watch: {
        countOngoingAlerts() {
            if (this.countOngoingAlerts) {
                GlancesFavico.badge(this.countOngoingAlerts);
            } else {
                GlancesFavico.reset();
            }
        }
    },
    methods: {
        formatDate(date) {
            return new Date(date).toLocaleString();
        }
    }
};
</script>