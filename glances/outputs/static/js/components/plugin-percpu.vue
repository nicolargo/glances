<template>
    <section id="percpu" class="plugin">
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left title" v-if="args.disable_quicklook">CPU</div>
                <div class="table-cell" v-if="args.disable_quicklook">total</div>
                <div class="table-cell">user</div>
                <div class="table-cell">system</div>
                <div class="table-cell">idle</div>
                <div class="table-cell">iowait</div>
                <div class="table-cell">steal</div>
            </div>
            <div class="table-row" v-for="(percpu, percpuId) in percpuStats" :key="percpuId">
                <div class="table-cell text-left" v-if="args.disable_quicklook">
                    CPU{{ percpu.cpu_number }}
                </div>
                <div class="table-cell" v-if="args.disable_quicklook">
                    {{ percpu.total }}%
                </div>
                <div class="table-cell" :class="getUserAlert(percpu)">
                    {{ percpu.user }}%
                </div>
                <div class="table-cell" :class="getSystemAlert(percpu)">
                    {{ percpu.system }}%
                </div>
                <div class="table-cell" v-show="percpu.idle != undefined">
                    {{ percpu.idle }}%
                </div>
                <div class="table-cell" v-show="percpu.iowait != undefined" :class="getIOWaitAlert(percpu)">
                    {{ percpu.iowait }}%
                </div>
                <div class="table-cell" v-show="percpu.steal != undefined">
                    {{ percpu.steal }}%
                </div>
            </div>
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