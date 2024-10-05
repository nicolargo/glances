<template>
    <section id="gpu" class="plugin" v-if="gpus != undefined">
        <div class="title gpu-name">{{ name }}</div>
        <!-- single gpu -->
        <template v-if="gpus.length === 1">
            <div class="table-responsive">
                <template v-for="(gpu, gpuId) in gpus" :key="gpuId">
                    <table class="table table-sm table-borderless">
                        <tbody>
                            <tr>
                                <td class="col">proc:</td>
                                <td class="col text-end" :class="getDecoration(gpu.gpu_id, 'proc')" v-if="gpu.proc != null">{{ $filters.number(gpu.proc, 0) }}%</td>
                                <td class="col text-end" v-if="gpu.proc == null">N/A</td>
                            </tr>
                            <tr>
                                <td class="col">mem:</td>
                                <td class="col text-end" :class="getDecoration(gpu.gpu_id, 'mem')" v-if="gpu.mem != null">{{ $filters.number(gpu.mem, 0) }}%</td>
                                <td class="col text-end" v-if="gpu.mem == null">N/A</td>
                            </tr>
                            <tr>
                                <td class="col">temp:</td>
                                <td class="col text-end" :class="getDecoration(gpu.gpu_id, 'temperature')" v-if="gpu.temperature != null">{{ $filters.number(gpu.temperature, 0) }}</td>
                                <td class="col text-end" v-if="gpu.temperature == null">N/A</td>
                            </tr>
                        </tbody>
                    </table>
                </template>
            </div>
        </template>
        <!-- multiple gpus - one line per gpu (no mean) -->
        <template v-if="!args.meangpu && gpus.length > 1">
            <div class="table-responsive">
                <table class="table table-sm table-borderless">
                    <tbody>
                        <tr v-for="(gpu, gpuId) in gpus" :key="gpuId">
                            <td class="col">{{ gpu.gpu_id }}:</td>
                            <td class="col" :class="getDecoration(gpu.gpu_id, 'proc')" v-if="gpu.proc != null">{{ $filters.number(gpu.proc, 0) }}%</td>
                            <td class="col" v-if="gpu.proc == null">N/A</td>
                            <td class="col">mem:</td>
                            <td class="col text-end" :class="getDecoration(gpu.gpu_id, 'mem')" v-if="gpu.mem != null">{{ $filters.number(gpu.mem, 0) }}%</td>
                            <td class="col text-end" v-if="gpu.mem == null">N/A</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </template>
        <!-- multiple gpus - mean -->
        <template v-if="args.meangpu && gpus.length > 1">
            <div class="table-responsive">
                <table class="table table-sm table-borderless">
                    <tbody>
                        <tr>
                            <td class="col">proc mean:</td>
                            <td class="col" :class="getMeanDecoration('proc')" v-if="mean.proc != null">
                                {{ $filters.number(mean.proc, 0) }}%
                            </td>
                            <td class="col" v-if="mean.proc == null">N/A</td>
                        </tr>
                        <tr>
                            <td class="col">mem mean:</td>
                            <td class="col" :class="getMeanDecoration('mem')" v-if="mean.mem != null">
                                {{ $filters.number(mean.mem, 0) }}%
                            </td>
                            <td class="col" v-if="mean.mem == null">N/A</td>
                        </tr>
                        <tr>
                            <td class="col">temp mean:</td>
                            <td class="col" :class="getMeanDecoration('temperature')" v-if="mean.temperature != null">
                                {{ $filters.number(mean.temperature, 0) }}
                            </td>
                            <td class="col" v-if="mean.temperature == null">N/A</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </template>
    </section>
</template>

<script>
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
            return this.data.stats['gpu'];
        },
        view() {
            return this.data.views['gpu'];
        },
        gpus() {
            return this.stats;
        },
        name() {
            let name = 'GPU';
            const sameName = true;
            const { stats } = this;
            if (stats.length === 1) {
                name = stats[0].name;
            } else if (stats.length && sameName) {
                name = `${stats.length} GPU ${stats[0].name}`;
            }
            return name;
        },
        mean() {
            const mean = {
                proc: null,
                mem: null,
                temperature: null
            };
            const { stats } = this;
            if (!stats.length) {
                return mean;
            }
            for (let gpu of stats) {
                mean.proc += gpu.proc;
                mean.mem += gpu.mem;
                mean.temperature += gpu.temperature;
            }
            mean.proc = mean.proc / stats.length;
            mean.mem = mean.mem / stats.length;
            mean.temperature = mean.temperature / stats.length;
            return mean;
        }
    },
    methods: {
        getDecoration(gpuId, value) {
            if (this.view[gpuId][value] === undefined) {
                return;
            }
            return this.view[gpuId][value].decoration.toLowerCase();
        },
        getMeanDecoration(value) {
            return 'DEFAULT';
        }
    }
};
</script>