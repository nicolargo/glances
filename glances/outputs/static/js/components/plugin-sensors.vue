<template>
    <section class="plugin" id="sensors">
        <div class="table-row" v-if="sensors.length > 0">
            <div class="table-cell text-left title">SENSORS</div>
        </div>
        <div class="table-row" v-for="(sensor, sensorId) in sensors" :key="sensorId">
            <div class="table-cell text-left">{{ sensor.label }}</div>
            <div class="table-cell">{{ sensor.unit }}</div>
            <div class="table-cell" :class="getAlert(sensor)">
                {{ sensor.value }}
            </div>
        </div>
    </section>
</template>

<script>
import { GlancesHelper } from '../services.js';
import { store } from '../store.js';

export default {
    props: {
        data: {
            type: Object
        }
    },
    data() {
        return {
            store
        };
    },
    computed: {
        args() {
            return this.store.args || {};
        },
        stats() {
            return this.data.stats['sensors'];
        },
        sensors() {
            return this.stats
                .filter((sensor) => {
                    // prettier-ignore
                    const isEmpty = (Array.isArray(sensor.value) && sensor.value.length === 0) || sensor.value === 0;
                    return !isEmpty;
                })
                .map((sensor) => {
                    if (
                        this.args.fahrenheit &&
                        sensor.type != 'battery' &&
                        sensor.type != 'fan_speed'
                    ) {
                        // prettier-ignore
                        sensor.value = parseFloat(sensor.value * 1.8 + 32).toFixed(1);
                        sensor.unit = 'F';
                    }
                    return sensor;
                });
        }
    },
    methods: {
        getAlert(sensor) {
            const current = sensor.type == 'battery' ? 100 - sensor.value : sensor.value;
            return GlancesHelper.getAlert('sensors', 'sensors_' + sensor.type + '_', current);
        }
    }
};
</script>