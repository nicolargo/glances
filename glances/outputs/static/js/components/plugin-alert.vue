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
                        ({{ alert.ongoing ? 'ongoing' : alert.duration }}) -
                        <span v-show="!alert.ongoing"> {{ alert.level }} on </span>
                        <span :class="alert.level.toLowerCase()">
                            {{ alert.name }}
                        </span>
                        ({{ $filters.number(alert.max, 1) }})
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
                alert.name = alertalertStats[3];
                alert.level = alertalertStats[2];
                alert.begin = alertalertStats[0] * 1000;
                alert.end = alertalertStats[1] * 1000;
                alert.ongoing = alertalertStats[1] == -1;
                alert.min = alertalertStats[6];
                alert.mean = alertalertStats[5];
                alert.max = alertalertStats[4];

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
            return new Date(date)
                .toISOString()
                .slice(0, 19)
                .replace(/[^\d-:]/, ' ');
        }
    }
};
</script>