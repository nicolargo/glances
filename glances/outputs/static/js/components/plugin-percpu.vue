<template>
    <section id="percpu" class="plugin">
        <!-- d-none d-xl-block d-xxl-block -->
        <div class="table-responsive">
            <table class="table table-sm table-borderless">
                <thead>
                    <tr>
                        <th scope="col" v-if="args.disable_quicklook">CPU</th>
                        <td scope="col" v-if="args.disable_quicklook">total</td>
                        <td scope="col">user</td>
                        <td scope="col">system</td>
                        <td scope="col">idle</td>
                        <td scope="col">iowait</td>
                        <td scope="col">steel</td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(percpu, percpuId) in percpuStats" :key="percpuId">
                        <td scope="col" v-if="args.disable_quicklook">CPU{{ percpu.cpu_number }}</td>
                        <td scope="col" v-if="args.disable_quicklook">{{ percpu.total }}%</td>
                        <td scope="col" :class="getUserAlert(percpu)">{{ percpu.user }}%</td>
                        <td scope="col" :class="getSystemAlert(percpu)">{{ percpu.system }}%</td>
                        <td scope="col" v-show="percpu.idle != undefined">{{ percpu.idle }}%</td>
                        <td scope="col" v-show="percpu.iowait != undefined" :class="getIOWaitAlert(percpu)">{{ percpu.iowait }}%</td>
                        <td scope="col" v-show="percpu.steal != undefined">{{ percpu.steal }}%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
</template>

<script>
import { store } from '../store.js';
import { GlancesHelper } from '../services.js';
import { chunk } from 'lodash';

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
        config() {
            return this.store.config || {};
        },
        percpuStats() {
            return this.data.stats['percpu'];
        }
    },
    methods: {
        getUserAlert(cpu) {
            return GlancesHelper.getAlert('percpu', 'percpu_user_', cpu.user);
        },
        getSystemAlert(cpu) {
            return GlancesHelper.getAlert('percpu', 'percpu_system_', cpu.system);
        },
        getIOWaitAlert(cpu) {
            return GlancesHelper.getAlert('percpu', 'percpu_iowait_', cpu.system);
        }
    }
};
</script>