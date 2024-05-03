<template>
    <section id="quicklook" class="plugin">
        <div class="cpu-name text-left">
            {{ cpu_name }}
        </div>
        <!-- <div class="cpu-freq text-right" v-if="cpu_hz_current">
            {{ cpu_hz_current }}/{{ cpu_hz }}Ghz
        </div> -->
        <div class="table">
            <div class="table-row" v-if="!args.percpu">
                <div class="table-cell text-left">CPU</div>
                <div class="table-cell">
                    <div class="progress">
                        <div
                            :class="`progress-bar progress-bar-${getDecoration('cpu')}`"
                            role="progressbar"
                            :aria-valuenow="cpu"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            :style="`width: ${cpu}%;`"
                        >
                            &nbsp;
                        </div>
                    </div>
                </div>
                <div class="table-cell">{{ cpu }}%</div>
            </div>
            <template v-if="args.percpu">
                <div class="table-row" v-for="(percpu, percpuId) in percpus" :key="percpuId">
                    <div class="table-cell text-left">CPU{{ percpu.number }}</div>
                    <div class="table-cell">
                        <div class="progress">
                            <div
                                :class="`progress-bar progress-bar-${getDecoration('cpu')}`"
                                role="progressbar"
                                :aria-valuenow="percpu.total"
                                aria-valuemin="0"
                                aria-valuemax="100"
                                :style="`width: ${percpu.total}%;`"
                            >
                                &nbsp;
                            </div>
                        </div>
                    </div>
                    <div class="table-cell">{{ percpu.total }}%</div>
                </div>
            </template>
            <div class="table-row" v-for="(key) in stats_list_after_cpu">
                <div class="table-cell text-left">{{ key.toUpperCase() }}</div>
                <div class="table-cell">
                    <div class="progress">
                        <div
                            :class="`progress-bar progress-bar-${getDecoration(key)}`"
                            role="progressbar"
                            :aria-valuenow="stats[key]"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            :style="`width: ${stats[key]}%;`"
                        >
                            &nbsp;
                        </div>
                    </div>
                </div>
                <div class="table-cell">{{ stats[key] }}%</div>
            </div>
        </div>
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
        config() {
            return this.store.config || {};
        },
        stats() {
            return this.data.stats['quicklook'];
        },
        view() {
            return this.data.views['quicklook'];
        },
        cpu() {
            return this.stats.cpu;
        },
        cpu_name() {
            return this.stats.cpu_name;
        },
        cpu_hz_current() {
            return this.stats.cpu_hz_current;
        },
        cpu_hz() {
            return this.stats.cpu_hz;
        },
        percpus() {
            var cpu_list = this.stats.percpu.map(({ cpu_number: number, total }) => ({ number, total }))
            var max_cpu_display = parseInt(this.config.percpu.max_cpu_display)
            if (this.stats.percpu.length > max_cpu_display) {
                var cpu_list_sorted = cpu_list.sort(function (a, b) { return b.total - a.total; })
                var other_cpu = {
                    number: "x",
                    total: Number((cpu_list_sorted.slice(max_cpu_display).reduce((n, { total }) => n + total, 0) / (this.stats.percpu.length - max_cpu_display)).toFixed(1))
                }
                // Add the top n this
                // and the mean of others CPU
                cpu_list_sorted = cpu_list_sorted.slice(0, max_cpu_display)
                cpu_list_sorted.push(other_cpu)
            }
            return this.stats.percpu.length <= max_cpu_display
                ? cpu_list
                : cpu_list_sorted
        },
        stats_list_after_cpu() {
            return this.view.list.filter((key) => !key.includes('cpu'));
        },
    },
    methods: {
        getDecoration(value) {
            if (this.view[value] === undefined) {
                return;
            }
            return this.view[value].decoration.toLowerCase();
        }
    }
};
</script>