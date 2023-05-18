<template>
    <section class="plugin" id="network">
        <div class="table-row">
            <div class="table-cell text-left title">NETWORK</div>
            <div class="table-cell" v-show="!args.network_cumul && !args.network_sum">Rx/s</div>
            <div class="table-cell" v-show="!args.network_cumul && !args.network_sum">Tx/s</div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum">Rx+Tx/s</div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">Rx</div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">Tx</div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum">Rx+Tx</div>
        </div>
        <div class="table-row" v-for="(network, networkId) in networks" :key="networkId">
            <div class="table-cell text-left">
                <span class="visible-lg-inline">{{ network.ifname }}</span>
                <span class="hidden-lg">{{ $filters.minSize(network.ifname) }}</span>
            </div>
            <div class="table-cell" v-show="!args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.rx / network.time_since_update) : $filters.bits(network.rx / network.time_since_update) }}
            </div>
            <div class="table-cell" v-show="!args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.tx / network.time_since_update) : $filters.bits(network.tx / network.time_since_update) }}
            </div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum">
                {{ args.byte ? $filters.bytes(network.cx / network.time_since_update) : $filters.bits(network.cx / network.time_since_update) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.cumulativeRx) : $filters.bits(network.cumulativeRx) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.cumulativeTx) : $filters.bits(network.cumulativeTx) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum">
                {{ args.byte ? $filters.bytes(network.cumulativeCx) : $filters.bits(network.cumulativeCx) }}
            </div>
        </div>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
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
            return this.data.stats['network'];
        },
        networks() {
            const networks = this.stats.map((networkData) => {
                const alias = networkData['alias'] !== undefined ? networkData['alias'] : null;

                const network = {
                    interfaceName: networkData['interface_name'],
                    ifname: alias ? alias : networkData['interface_name'],
                    rx: networkData['rx'],
                    tx: networkData['tx'],
                    cx: networkData['cx'],
                    time_since_update: networkData['time_since_update'],
                    cumulativeRx: networkData['cumulative_rx'],
                    cumulativeTx: networkData['cumulative_tx'],
                    cumulativeCx: networkData['cumulative_cx']
                };

                return network;
            });
            return orderBy(networks, ['interfaceName']);
        }
    }
};
</script>