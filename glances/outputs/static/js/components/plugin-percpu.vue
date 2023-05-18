<template>
    <section id="percpu" class="plugin">
        <div class="table" v-for="(cpus, cpusChunkId) in cpusChunks" :key="cpusChunkId">
            <div class="table-row">
                <div class="table-cell text-left title">
                    <span v-if="cpusChunkId === 0">PER CPU</span>
                </div>
                <div class="table-cell" v-for="(percpu, percpuId) in cpus" :key="percpuId">
                    {{ percpu.total }}%
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">user:</div>
                <div
                    class="table-cell"
                    v-for="(percpu, percpuId) in cpus"
                    :key="percpuId"
                    :class="getUserAlert(percpu)"
                >
                    {{ percpu.user }}%
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">system:</div>
                <div
                    class="table-cell"
                    v-for="(percpu, percpuId) in cpus"
                    :key="percpuId"
                    :class="getSystemAlert(percpu)"
                >
                    {{ percpu.system }}%
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">idle:</div>
                <div class="table-cell" v-for="(percpu, percpuId) in cpus" :key="percpuId">
                    {{ percpu.idle }}%
                </div>
            </div>
            <div class="table-row" v-if="cpus[0].iowait">
                <div class="table-cell text-left">iowait:</div>
                <div
                    class="table-cell"
                    v-for="(percpu, percpuId) in cpus"
                    :key="percpuId"
                    :class="getSystemAlert(percpu)"
                >
                    {{ percpu.iowait }}%
                </div>
            </div>
            <div class="table-row" v-if="cpus[0].steal">
                <div class="table-cell text-left">steal:</div>
                <div
                    class="table-cell"
                    v-for="(percpu, percpuId) in cpus"
                    :key="percpuId"
                    :class="getSystemAlert(percpu)"
                >
                    {{ percpu.steal }}%
                </div>
            </div>
        </div>
    </section>
</template>

<script>
import { GlancesHelper } from '../services.js';
import { chunk } from 'lodash';

export default {
    props: {
        data: {
            type: Object
        }
    },
    computed: {
        percpuStats() {
            return this.data.stats['percpu'];
        },
        cpusChunks() {
            const retval = this.percpuStats.map((cpuData) => {
                return {
                    number: cpuData.cpu_number,
                    total: cpuData.total,
                    user: cpuData.user,
                    system: cpuData.system,
                    idle: cpuData.idle,
                    iowait: cpuData.iowait,
                    steal: cpuData.steal
                };
            });
            return chunk(retval, 4);
        }
    },
    methods: {
        getUserAlert(cpu) {
            return GlancesHelper.getAlert('percpu', 'percpu_user_', cpu.user);
        },
        getSystemAlert(cpu) {
            return GlancesHelper.getAlert('percpu', 'percpu_system_', cpu.system);
        }
    }
};
</script>