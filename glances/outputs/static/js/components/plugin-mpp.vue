<template>
    <section v-if="engines != undefined && engines.length > 0" id="mpp" class="plugin">
        <div class="table-responsive">
            <div class="title">MPP</div>
            <table class="table table-sm table-borderless">
                <tbody>
                    <tr v-for="(engine, idx) in engines" :key="idx">
                        <td class="col">
                            <span>{{ engine.name }}</span>
                        </td>
                        <td class="col" :class="getDecoration(engine.engine_id, 'load')">
                            <span v-if="engine.load != null">{{ $filters.number(engine.load, 1) }}%</span>
                            <span v-else>N/A</span>
                        </td>
                        <td class="col text-end">
                            <span v-if="engine.sessions > 0">{{ engine.sessions }} sess</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
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
            return this.data.stats["mpp"];
        },
        view() {
            return this.data.views["mpp"];
        },
        engines() {
            return this.stats;
        },
    },
    methods: {
        getDecoration(engineId, value) {
            if (
                this.view[engineId] === undefined ||
                this.view[engineId][value] === undefined
            ) {
                return;
            }
            return this.view[engineId][value].decoration.toLowerCase();
        },
    },
};
</script>
