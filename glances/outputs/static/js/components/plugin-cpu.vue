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
                    <div class="table-row" v-if="nice == undefined && ctx_switches != undefined">
                        <div class="table-cell text-left">ctx_sw:</div>
                        <div class="table-cell" :class="getDecoration('ctx_switches')">
                            {{ ctx_switches }}
                        </div>
                    </div>
                    <div class="table-row" v-show="steal != undefined">
                        <div class="table-cell text-left">steal:</div>
                        <div class="table-cell" :class="getDecoration('steal')">{{ steal }}%</div>
                    </div>
                    <div class="table-row" v-if="!isLinux && syscalls != undefined">
                        <div class="table-cell text-left">syscal:</div>
                        <div class="table-cell">{{ syscalls }}</div>
                    </div>
                </div>
            </div>
            <div class="hidden-xs hidden-sm hidden-md col-lg-8">
                <div class="table">
                    <!-- If not already display instead of nice, then display ctx_switches -->
                    <div class="table-row" v-if="nice != undefined && ctx_switches != undefined">
                        <div class="table-cell text-left">ctx_sw:</div>
                        <div class="table-cell" :class="getDecoration('ctx_switches')">
                            {{ ctx_switches }}
                        </div>
                    </div>
                    <!-- If not already display instead of irq, then display interrupts -->
                    <div class="table-row" v-if="irq != undefined && interrupts != undefined">
                        <div class="table-cell text-left">inter:</div>
                        <div class="table-cell">
                            {{ interrupts }}
                        </div>
                    </div>
                    <div class="table-row" v-if="!isWindows && !isSunOS && soft_interrupts != undefined">
                        <div class="table-cell text-left">sw_int:</div>
                        <div class="table-cell">
                            {{ soft_interrupts }}
                        </div>
                    </div>
                    <div class="table-row" v-if="isLinux && guest != undefined">
                        <div class="table-cell text-left">guest:</div>
                        <div class="table-cell">{{ guest }}%</div>
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
        guest() {
            return this.stats.guest;
        },
        ctx_switches() {
            const { stats } = this;
            return stats.ctx_switches
                ? Math.floor(stats.ctx_switches / stats.time_since_update)
                : null;
        },
        interrupts() {
            const { stats } = this;
            return stats.interrupts ? Math.floor(stats.interrupts / stats.time_since_update) : null;
        },
        soft_interrupts() {
            const { stats } = this;
            return stats.soft_interrupts
                ? Math.floor(stats.soft_interrupts / stats.time_since_update)
                : null;
        },
        syscalls() {
            const { stats } = this;
            return stats.syscalls ? Math.floor(stats.syscalls / stats.time_since_update) : null;
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