<template>
    <section class="plugin" id="ports">
        <div class="table-row" v-for="(port, portId) in ports" :key="portId">
            <div class="table-cell text-left">
                <!-- prettier-ignore -->
                {{ $filters.minSize(port.description ? port.description : port.host + ' ' + port.port, 20) }}
            </div>
            <div class="table-cell"></div>
            <div :class="getPortDecoration(port)" class="table-cell" v-if="port.host">
                <span v-if="port.status == 'null'">Scanning</span>
                <span v-else-if="port.status == 'false'">Timeout</span>
                <span v-else-if="port.status == 'true'">Open</span>
                <span v-else>{{ $filters.number(port.status * 1000.0, 0) }}ms</span>
            </div>
            <div :class="getWebDecoration(port)" class="table-cell" v-if="port.url">
                <span v-if="port.status == 'null'">Scanning</span>
                <span v-else-if="port.status == 'Error'">Error</span>
                <span v-else>Code {{ port.status }}</span>
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
            return this.data.stats['ports'];
        },
        ports() {
            return this.stats;
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