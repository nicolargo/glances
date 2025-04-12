<template>
    <section id="cpu" class="plugin">
        <!-- d-none d-xxl-block -->
        <div class="table-responsive">
            <table class="table-sm table-borderless">
                <tbody>
                    <tr class="justify-content-between">
                        <td scope="col">
                            <table class="table table-sm table-borderless">
                                <tbody>
                                    <tr>
                                        <th scope="col">CPU</th>
                                        <td scope="col" class="text-end" :class="getDecoration('total')"><span>{{
                                            total }}%</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td scope="col">user:</td>
                                        <td scope="col" class="text-end" :class="getDecoration('user')"><span>{{
                                            user }}%</span></td>
                                    </tr>
                                    <tr>
                                        <td scope="col">system:</td>
                                        <td scope="col" class="text-end" :class="getDecoration('system')"><span>{{
                                            system }}%</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td v-if="iowait != undefined" scope="col">iowait:</td>
                                        <td
v-if="iowait != undefined" scope="col" class="text-end"
                                            :class="getDecoration('iowait')"><span>{{ iowait }}%</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                        <td>
                            <template class="d-none d-xl-block d-xxl-block">
                                <table class="table table-sm table-borderless">
                                    <tbody>
                                        <tr>
                                            <td v-show="idle != undefined" scope="col">idle:</td>
                                            <td v-show="idle != undefined" scope="col" class="text-end"><span>{{ idle
                                                    }}%</span></td>
                                        </tr>
                                        <tr>
                                            <td v-show="irq != undefined" scope="col">irq:</td>
                                            <td v-show="irq != undefined" scope="col" class="text-end"><span>{{ irq
                                                    }}%</span></td>
                                        </tr>
                                        <tr>
                                            <td v-show="nice != undefined" scope="col">nice:</td>
                                            <td v-show="nice != undefined" scope="col" class="text-end"><span>{{ nice
                                                    }}%</span></td>
                                        </tr>
                                        <tr>
                                            <td v-if="iowait == undefined && dpc != undefined" scope="col">dpc:</td>
                                            <td
v-if="iowait == undefined && dpc != undefined" scope="col"
                                                class="text-end"
                                                :class="getDecoration('dpc')"><span>{{ dpc
                                                    }}%</span></td>
                                            <td v-show="steal != undefined" scope="col">steal:</td>
                                            <td
v-show="steal != undefined" scope="col" class="text-end"
                                                :class="getDecoration('steal')"><span>{{ steal
                                                    }}%</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </template>
                        </td>
                        <td>
                            <template class="d-none d-xxl-block">
                                <table class="table table-sm table-borderless">
                                    <tbody>
                                        <tr>
                                            <td v-if="nice != undefined && ctx_switches != undefined" scope="col">
                                                ctx_sw:</td>
                                            <td
v-if="nice != undefined && ctx_switches != undefined" scope="col"
                                                class="text-end"
                                                :class="getDecoration('ctx_switches')"><span>{{ ctx_switches
                                                    }}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td v-show="interrupts != undefined" scope="col">inter:</td>
                                            <td v-show="interrupts != undefined" scope="col" class="text-end"><span>{{
                                                interrupts
                                            }}</span></td>
                                        </tr>
                                        <tr>
                                            <td
v-if="!isWindows && !isSunOS && soft_interrupts != undefined"
                                                scope="col">sw_int:
                                            </td>
                                            <td
v-if="!isWindows && !isSunOS && soft_interrupts != undefined" scope="col"
                                                class="text-end"><span>{{
                                                    soft_interrupts
                                                }}</span></td>
                                        </tr>
                                        <tr>
                                            <td v-if="isLinux && guest != undefined" scope="col">guest:</td>
                                            <td v-if="isLinux && guest != undefined" scope="col" class="text-end">
                                                <span>{{
                                                    guest
                                                    }}%</span>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </table>
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