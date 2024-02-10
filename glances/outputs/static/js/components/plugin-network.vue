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
                {{ args.byte ? $filters.bytes(network.bytes_recv_rate_per_sec) : $filters.bits(network.bytes_recv_rate_per_sec) }}
            </div>
            <div class="table-cell" v-show="!args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.bytes_sent_rate_per_sec) : $filters.bits(network.bytes_sent_rate_per_sec) }}
            </div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="!args.network_cumul && args.network_sum">
                {{ args.byte ? $filters.bytes(network.bytes_all_rate_per_sec) : $filters.bits(network.bytes_all_rate_per_sec) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.bytes_recv) : $filters.bits(network.bytes_recv) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && !args.network_sum">
                {{ args.byte ? $filters.bytes(network.bytes_sent) : $filters.bits(network.bytes_sent) }}
            </div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum"></div>
            <div class="table-cell" v-show="args.network_cumul && args.network_sum">
                {{ args.byte ? $filters.bytes(network.bytes_all) : $filters.bits(network.bytes_all) }}
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
                    bytes_recv_rate_per_sec: networkData['bytes_recv_rate_per_sec'],
                    bytes_sent_rate_per_sec: networkData['bytes_sent_rate_per_sec'],
                    bytes_all_rate_per_sec: networkData['bytes_all_rate_per_sec'],
                    bytes_recv: networkData['bytes_recv'],
                    bytes_sent: networkData['bytes_sent'],
                    bytes_all: networkData['bytes_all']
                };

                return network;
            });
            return orderBy(networks, ['interfaceName']);
        }
    }
};
</script>