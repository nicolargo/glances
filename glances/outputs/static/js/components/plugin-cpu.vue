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
                                        <td scope="col" class="text-end" :class="getDecoration('total')">{{ total }}%</td>
                                    </tr>
                                    <tr>
                                        <td scope="col">user:</td>
                                        <td scope="col" class="text-end" :class="getDecoration('user')">{{ user }}%</td>
                                    </tr>
                                    <tr>
                                        <td scope="col">system:</td>
                                        <td scope="col" class="text-end" :class="getDecoration('system')">{{ system }}%</td>
                                    </tr>
                                    <tr>
                                        <td scope="col" v-if="iowait != undefined">iowait:</td>
                                        <td scope="col" class="text-end" v-if="iowait != undefined" :class="getDecoration('iowait')">{{ iowait }}%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                        <td>
                            <template class="d-none d-xl-block d-xxl-block">
                                <table class="table table-sm table-borderless">
                                    <tbody>
                                        <tr>
                                            <td scope="col" v-show="idle != undefined">idle:</td>
                                            <td scope="col" class="text-end" v-show="idle != undefined">{{ idle }}%</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="irq != undefined">irq:</td>
                                            <td scope="col" class="text-end" v-show="irq != undefined">{{ irq }}%</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="nice != undefined">nice:</td>
                                            <td scope="col" class="text-end" v-show="nice != undefined">{{ nice }}%</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-if="iowait == undefined && dpc != undefined">dpc:</td>
                                            <td scope="col" class="text-end" v-if="iowait == undefined && dpc != undefined" :class="getDecoration('dpc')">{{ dpc }}%</td>
                                            <td scope="col" v-show="steal != undefined">steal:</td>
                                            <td scope="col" class="text-end" v-show="steal != undefined" :class="getDecoration('steal')">{{ steal }}%</td>
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
                                            <td scope="col" v-if="nice != undefined && ctx_switches != undefined">ctx_sw:</td>
                                            <td scope="col"
                                                class="text-end"
                                                v-if="nice != undefined && ctx_switches != undefined"
                                                :class="getDecoration('ctx_switches')">{{ ctx_switches }}</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="interrupts != undefined">inter:</td>
                                            <td scope="col" class="text-end" v-show="interrupts != undefined">{{ interrupts }}</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-if="!isWindows && !isSunOS && soft_interrupts != undefined">sw_int:</td>
                                            <td scope="col" class="text-end" v-if="!isWindows && !isSunOS && soft_interrupts != undefined">{{ soft_interrupts }}</td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-if="isLinux && guest != undefined">guest:</td>
                                            <td scope="col" class="text-end" v-if="isLinux && guest != undefined">{{ guest }}%</td>
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