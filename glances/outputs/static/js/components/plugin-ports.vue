<template>
    <section class="plugin" id="ports" v-if="hasPorts">
        <table class="table table-sm table-borderless margin-bottom">
            <tbody>
                <tr v-for="(port, portId) in ports" :key="portId">
                    <td scope="row">
                        <!-- prettier-ignore -->
                        {{ $filters.minSize(port.description ? port.description : port.host + ' ' + port.port, 20) }}
                    </td>
                    <template v-if="port.host">
                        <td scope="row" class="text-end" :class="getPortDecoration(port)">
                            <span v-if="port.status == 'null'">Scanning</span>
                            <span v-else-if="port.status == 'false'">Timeout</span>
                            <span v-else-if="port.status == 'true'">Open</span>
                            <span v-else>{{ $filters.number(port.status * 1000.0, 0) }}ms</span>
                        </td>
                    </template>
                    <template v-if="port.url">
                        <td scope="row" class="text-end" :class="getPortDecoration(port)">
                            <span v-if="port.status == 'null'">Scanning</span>
                            <span v-else-if="port.status == 'Error'">Error</span>
                            <span v-else>Code {{ port.status }}</span>
                        </td>
                    </template>
                </tr>
            </tbody>
        </table>
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
            return this.data.stats['ports'];
        },
        ports() {
            return this.stats;
        },
        hasPorts() {
            return this.ports.length > 0;
        }
    },
    methods: {
        getPortDecoration(port) {
            if (port.status === null) {
                return 'careful';
            } else if (port.status === false) {
                return 'critical';
            } else if (port.rtt_warning !== null && port.status > port.rtt_warning) {
                return 'warning';
            }
            return 'ok';
        },
        getWebDecoration(web) {
            const okCodes = [200, 301, 302];

            if (web.status === null) {
                return 'careful';
            } else if (okCodes.indexOf(web.status) === -1) {
                return 'critical';
            } else if (web.rtt_warning !== null && web.elapsed > web.rtt_warning) {
                return 'warning';
            }

            return 'ok';
        }
    }
};
</script>