<template>
    <section class="plugin" id="gpu" v-if="gpus != undefined">
        <!-- single gpu -->
        <template v-if="gpus.length === 1">
            <div class="title gpu-name">{{ name }}</div>
            <div class="table">
                <template v-for="(gpu, gpuId) in gpus" :key="gpuId">
                    <div class="table-row">
                        <div class="table-cell text-left">proc:</div>
                        <div class="table-cell" :class="getDecoration(gpu.gpu_id, 'proc')" v-if="gpu.proc != null">{{ $filters.number(gpu.proc, 0) }}%</div>
                        <div class="table-cell" v-if="gpu.proc == null">N/A</div>
                    </div>
                    <div class="table-row">
                        <div class="table-cell text-left">mem:</div>
                        <div class="table-cell" :class="getDecoration(gpu.gpu_id, 'mem')" v-if="gpu.mem != null">{{ $filters.number(gpu.mem, 0) }}%</div>
                        <div class="table-cell" v-if="gpu.mem == null">N/A</div>
                    </div>
                    <div class="table-row">
                        <div class="table-cell text-left">temp:</div>
                        <div class="table-cell" :class="getDecoration(gpu.gpu_id, 'temperature')" v-if="gpu.temperature != null">{{ $filters.number(gpu.temperature, 0) }}°C</div>
                        <div class="table-cell" v-if="gpu.temperature == null">N/A</div>
                    </div>
                </template>
            </div>
        </template>

        <!-- multiple gpus - one line per gpu (no mean) -->
        <template v-if="!args.meangpu && gpus.length > 1">
            <div class="title gpu-name">{{ name }}</div>
            <div class="table">
                <div class="table-row" v-for="(gpu, gpuId) in gpus" :key="gpuId">
                    <div class="table-cell text-left">{{ gpu.gpu_id }}:</div>
                    <div class="table-cell" :class="getDecoration(gpu.gpu_id, 'proc')" v-if="gpu.proc != null">{{ $filters.number(gpu.proc, 0) }}%</div>
                    <div class="table-cell" v-if="gpu.proc == null">N/A</div>
                    <div class="table-cell text-left" style="padding-left: 10px">mem:</div>
                    <div class="table-cell" :class="getDecoration(gpu.gpu_id, 'mem')" v-if="gpu.mem != null">{{ $filters.number(gpu.mem, 0) }}%</div>
                    <div class="table-cell" v-if="gpu.mem == null">N/A</div>
                </div>
            </div>
        </template>

        <!-- multiple gpus - mean -->
        <template v-if="args.meangpu && gpus.length > 1">
            <div class="title gpu-name">{{ name }}</div>
            <div class="table">
                <div class="table-row">
                    <div class="table-cell text-left">proc mean:</div>
                    <div class="table-cell" :class="getMeanDecoration('proc')" v-if="mean.proc != null">
                        {{ $filters.number(mean.proc, 0) }}%
                    </div>
                    <div class="table-cell" v-if="mean.proc == null">N/A</div>
                </div>
                <div class="table-row">
                    <div class="table-cell text-left">mem mean:</div>
                    <div class="table-cell" :class="getMeanDecoration('mem')" v-if="mean.mem != null">
                        {{ $filters.number(mean.mem, 0) }}%
                    </div>
                    <div class="table-cell" v-if="mean.mem == null">N/A</div>
                </div>
                <div class="table-row">
                    <div class="table-cell text-left">temp mean:</div>
                    <div
                        class="table-cell"
                        :class="getMeanDecoration('temperature')"
                        v-if="mean.temperature != null"
                    >
                        {{ $filters.number(mean.temperature, 0) }}°
                    </div>
                    <div class="table-cell" v-if="mean.temperature == null">N/A</div>
                </div>
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