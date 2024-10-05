<template>
    <section class="plugin" id="sensors" v-if="hasSensors">
        <table class="table table-sm table-borderless">
            <thead>
                <tr>
                    <th scope="col">SENSORS</th>
                    <th scope="col" class="text-end"></th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(sensor, sensorId) in sensors" :key="sensorId">
                    <td scope="row">
                        {{ sensor.label }}
                    </td>
                    <td class="text-end" :class="getDecoration(sensor.label)">
                        {{ sensor.value }}{{ sensor.unit }}
                    </td>
                </tr>
            </tbody>
        </table>
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
        view() {
            return this.data.views['sensors'];
        },
        sensors() {
            return this.stats
                // .filter((sensor) => {
                //     // prettier-ignore
                //     const isEmpty = (Array.isArray(sensor.value) && sensor.value.length === 0) || sensor.value === 0;
                //     return !isEmpty;
                // })
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
        },
        hasSensors() {
            return this.sensors.length > 0;
        }
    },
    methods: {
        getDecoration(key) {
            if (this.view[key].value.decoration === undefined) {
                return;
            }
            return this.view[key].value.decoration.toLowerCase();
        }
    }
};
</script>