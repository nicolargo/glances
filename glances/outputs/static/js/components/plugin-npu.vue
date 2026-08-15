<template>
    <section v-if="npus != undefined" id="npu" class="plugin">
        <!-- single npu -->
        <template v-if="npus.length === 1">
            <div class="table-responsive">
                <template v-for="(npu, npuId) in npus" :key="npuId">
                    <div class="title text-truncate">{{ npu.name }}</div>
                    <table class="table table-sm table-borderless">
                        <tbody>
                            <tr>
                                <td v-if="npu.load != null" class="col" :class="getDecoration(npu.npu_id, 'load')">
                                    <span>{{ $filters.number(npu.load, 0)
                                    }}%</span>
                                </td>
                                <td v-if="npu.load == null" class="col" :class="getDecoration(npu.npu_id, 'freq')">
                                    <span>{{ $filters.number(npu.freq, 0)
                                        }}%</span>
                                </td>
                                <td class="col">
                                    <span>{{ $filters.number(npu.freq_current / 1000000000, 1) }}/{{
                                        $filters.number(npu.freq_max / 1000000000, 1)
                                    }}GHz</span>
                                </td>
                            </tr>
                            <tr>
                                <td class="col">mem:</td>
                                <td v-if="npu.mem != null" class="col text-end"
                                    :class="getDecoration(npu.npu_id, 'mem')"><span>{{ $filters.number(npu.mem, 0)
                                        }}%</span></td>
                                <td v-if="npu.mem == null" class="col text-end"><span>N/A</span></td>
                            </tr>
                            <tr>
                                <td class="col">temp:</td>
                                <td v-if="npu.temperature != null" class="col text-end"
                                    :class="getDecoration(npu.npu_id, 'temperature')"><span>
                                        {{ $filters.number(npu.temperature, 0) }}C
                                    </span></td>
                                <td v-if="npu.temperature == null" class="col text-end"><span>N/A</span></td>
                            </tr>
                        </tbody>
                    </table>
                </template>
            </div>
        </template>
        <!-- multiple npus - not implemented for the moment -->
    </section>
</template>

<script>
import { store } from "../store.js";

export default {
    props: {
        data: {
            type: Object,
        },
    },
    data() {
        return {
            store,
        };
    },
    computed: {
        args() {
            return this.store.args || {};
        },
        stats() {
            return this.data.stats["npu"];
        },
        view() {
            return this.data.views["npu"];
        },
        npus() {
            return this.stats;
        }
    },
    methods: {
        getDecoration(npuId, value) {
            if (this.view[npuId][value] === undefined) {
                return;
            }
            return this.view[npuId][value].decoration.toLowerCase();
        },
        getMeanDecoration(value) {
            return "DEFAULT";
        },
    },
};
</script>