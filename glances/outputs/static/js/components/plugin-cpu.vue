<template>
    <section id="cpu" class="plugin">
        <div class="row">
            <div class="col-sm-24 col-md-12 col-lg-8">
                <div class="table">
                    <div class="table-row">
                        <div class="table-cell text-left title">CPU</div>
                        <div class="table-cell" :class="getDecoration('total')">{{ total }}%</div>
                    </div>
                    <div class="table-row">
                        <div class="table-cell text-left">user:</div>
                        <div class="table-cell" :class="getDecoration('user')">{{ user }}%</div>
                    </div>
                    <div class="table-row">
                        <div class="table-cell text-left">system:</div>
                        <div class="table-cell" :class="getDecoration('system')">{{ system }}%</div>
                    </div>
                    <div class="table-row" v-show="iowait != undefined">
                        <div class="table-cell text-left">iowait:</div>
                        <div class="table-cell" :class="getDecoration('iowait')">{{ iowait }}%</div>
                    </div>
                    <div class="table-row" v-show="iowait == undefined && dpc != undefined">
                        <div class="table-cell text-left">dpc:</div>
                        <div class="table-cell" :class="getDecoration('dpc')">{{ dpc }}%</div>
                    </div>
                </div>
            </div>
            <div class="hidden-xs hidden-sm col-md-12 col-lg-8">
                <div class="table">
                    <div class="table-row">
                        <div class="table-cell text-left">idle:</div>
                        <div class="table-cell">{{ idle }}%</div>
                    </div>
                    <div class="table-row" v-show="irq != undefined">
                        <div class="table-cell text-left">irq:</div>
                        <div class="table-cell">{{ irq }}%</div>
                    </div>
                    <!-- If no irq, display interrupts -->
                    <div class="table-row" v-show="irq == undefined">
                        <div class="table-cell text-left">inter:</div>
                        <div class="table-cell">
                            {{ interrupts }}
                        </div>
                    </div>
                    <div class="table-row" v-show="nice != undefined">
                        <div class="table-cell text-left">nice:</div>
                        <div class="table-cell">{{ nice }}%</div>
                    </div>
                    <!-- If no nice, display ctx_switches -->
                    <div class="table-row" v-if="nice == undefined && ctx_switches">
                        <div class="table-cell text-left">ctx_sw:</div>
                        <div class="table-cell" :class="getDecoration('ctx_switches')">
                            {{ ctx_switches }}
                        </div>
                    </div>
                    <div class="table-row" v-show="steal != undefined">
                        <div class="table-cell text-left">steal:</div>
                        <div class="table-cell" :class="getDecoration('steal')">{{ steal }}%</div>
                    </div>
                    <div class="table-row" v-if="!isLinux && syscalls">
                        <div class="table-cell text-left">syscal:</div>
                        <div class="table-cell">
                            {{ $filters.bytes(syscalls) }}
                        </div>
                    </div>
                </div>
            </div>
            <div class="hidden-xs hidden-sm hidden-md col-lg-8">
                <div class="table">
                    <!-- If not already display instead of nice, then display ctx_switches -->
                    <div class="table-row" v-if="nice != undefined && ctx_switches">
                        <div class="table-cell text-left">ctx_sw:</div>
                        <div class="table-cell" :class="getDecoration('ctx_switches')">
                            {{ $filters.bytes(ctx_switches) }}
                        </div>
                    </div>
                    <!-- If not already display instead of irq, then display interrupts -->
                    <div class="table-row" v-if="irq != undefined && interrupts">
                        <div class="table-cell text-left">inter:</div>
                        <div class="table-cell">
                            {{ $filters.bytes(interrupts) }}
                        </div>
                    </div>
                    <div class="table-row" v-if="!isWindows && !isSunOS && soft_interrupts">
                        <div class="table-cell text-left">sw_int:</div>
                        <div class="table-cell">
                            {{ $filters.bytes(soft_interrupts) }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>

<script>
export default {
    props: {
        data: {
            type: Object
        }
    },
    computed: {
        stats() {
            return this.data.stats['cpu'];
        },
        view() {
            return this.data.views['cpu'];
        },
        isLinux() {
            return this.data.isLinux;
        },
        isSunOS() {
            return this.data.isSunOS;
        },
        isWindows() {
            return this.data.isWindows;
        },
        total() {
            return this.stats.total;
        },
        user() {
            return this.stats.user;
        },
        system() {
            return this.stats.system;
        },
        idle() {
            return this.stats.idle;
        },
        nice() {
            return this.stats.nice;
        },
        irq() {
            return this.stats.irq;
        },
        iowait() {
            return this.stats.iowait;
        },
        dpc() {
            return this.stats.dpc;
        },
        steal() {
            return this.stats.steal;
        },
        ctx_switches() {
            return this.stats.ctx_switches;
        },
        interrupts() {
            return this.stats.interrupts;
        },
        soft_interrupts() {
            return this.stats.soft_interrupts;
        },
        syscalls() {
            return this.stats.syscalls;
        }
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