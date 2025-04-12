<template>
    <section v-if="gpus != undefined" id="gpu" class="plugin">
        <div class="title text-truncate">{{ name }}</div>
        <!-- single gpu -->
        <template v-if="gpus.length === 1">
            <div class="table-responsive">
                <template v-for="(gpu, gpuId) in gpus" :key="gpuId">
                    <table class="table table-sm table-borderless">
                        <tbody>
                            <tr>
                                <td class="col">proc:</td>
                                <td
v-if="gpu.proc != null" class="col text-end"
                                    :class="getDecoration(gpu.gpu_id, 'proc')"><span>{{ $filters.number(gpu.proc, 0) }}%</span></td>
                                <td v-if="gpu.proc == null" class="col text-end"><span>N/A</span></td>
                            </tr>
                            <tr>
                                <td class="col">mem:</td>
                                <td
v-if="gpu.mem != null" class="col text-end"
                                    :class="getDecoration(gpu.gpu_id, 'mem')"><span>{{ $filters.number(gpu.mem, 0) }}%</span></td>
                                <td v-if="gpu.mem == null" class="col text-end"><span>N/A</span></td>
                            </tr>
                            <tr>
                                <td class="col">temp:</td>
                                <td
v-if="gpu.temperature != null" class="col text-end"
                                    :class="getDecoration(gpu.gpu_id, 'temperature')"><span>
                                        {{ $filters.number(gpu.temperature, 0) }}
                                    </span></td>
                                <td v-if="gpu.temperature == null" class="col text-end"><span>N/A</span></td>
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
                            <td v-if="gpu.proc != null" class="col" :class="getDecoration(gpu.gpu_id, 'proc')"><span>{{
                                $filters.number(gpu.proc, 0) }}%</span></td>
                            <td v-if="gpu.proc == null" class="col"><span>N/A</span></td>
                            <td class="col">mem:</td>
                            <td v-if="gpu.mem != null" class="col text-end" :class="getDecoration(gpu.gpu_id, 'mem')">
                                <span>
                                    {{ $filters.number(gpu.mem, 0) }}%
                                </span>
                            </td>
                            <td v-if="gpu.mem == null" class="col text-end"><span>N/A</span></td>
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
                            <td v-if="mean.proc != null" class="col" :class="getMeanDecoration('proc')">
                                <span>{{ $filters.number(mean.proc, 0) }}%</span>
                            </td>
                            <td v-if="mean.proc == null" class="col"><span>N/A</span>></td>
                        </tr>
                        <tr>
                            <td class="col">mem mean:</td>
                            <td v-if="mean.mem != null" class="col" :class="getMeanDecoration('mem')">
                                <span>{{ $filters.number(mean.mem, 0) }}%</span>
                            </td>
                            <td v-if="mean.mem == null" class="col"><span>N/A</span></td>
                        </tr>
                        <tr>
                            <td class="col">temp mean:</td>
                            <td v-if="mean.temperature != null" class="col" :class="getMeanDecoration('temperature')">
                                <span>{{ $filters.number(mean.temperature, 0) }}°C</span>
                            </td>
                            <td v-if="mean.temperature == null" class="col"><span>N/A</span></td>
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
            for (const gpu of stats) {
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