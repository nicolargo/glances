<template>
    <section v-if="hasNetworks" id="network" class="plugin">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">NETWORK</th>
                    <th v-show="!args.network_cumul && !args.network_sum" scope="col" class="text-end w-25">Rxps</th>
                    <th v-show="!args.network_cumul && !args.network_sum" scope="col" class="text-end w-25">Txps</th>
                    <th v-show="!args.network_cumul && args.network_sum" scope="col" class="text-end w-25"></th>
                    <th v-show="!args.network_cumul && args.network_sum" scope="col" class="text-end w-25">Rx+Txps</th>
                    <th v-show="args.network_cumul && !args.network_sum" scope="col" class="text-end w-25">Rx</th>
                    <th v-show="args.network_cumul && !args.network_sum" scope="col" class="text-end w-25">Tx</th>
                    <th v-show="args.network_cumul && args.network_sum" scope="col" class="text-end w-25"></th>
                    <th v-show="args.network_cumul && args.network_sum" scope="col" class="text-end w-25">Rx+Tx</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(network, networkId) in networks" :key="networkId">
                    <td scope="row" class="visible-lg-inline text-truncate">
                        {{ $filters.minSize(network.alias ? network.alias : network.ifname, 16) }}
                    </td>
                    <td
v-show="!args.network_cumul && !args.network_sum" class="text-end"
                        :class="getDecoration(network.interfaceName, 'bytes_recv_rate_per_sec')">
                        {{ args.byte ? $filters.bytes(network.bytes_recv_rate_per_sec) :
                            $filters.bits(network.bytes_recv_rate_per_sec) }}
                    </td>
                    <td
v-show="!args.network_cumul && !args.network_sum" class="text-end"
                        :class="getDecoration(network.interfaceName, 'bytes_sent_rate_per_sec')">
                        {{ args.byte ? $filters.bytes(network.bytes_sent_rate_per_sec) :
                            $filters.bits(network.bytes_sent_rate_per_sec) }}
                    </td>
                    <td v-show="!args.network_cumul && args.network_sum" class="text-end"></td>
                    <td v-show="!args.network_cumul && args.network_sum" class="text-end">
                        {{ args.byte ? $filters.bytes(network.bytes_all_rate_per_sec) :
                            $filters.bits(network.bytes_all_rate_per_sec) }}
                    </td>
                    <td v-show="args.network_cumul && !args.network_sum" class="text-end">
                        {{ args.byte ? $filters.bytes(network.bytes_recv) : $filters.bits(network.bytes_recv) }}
                    </td>
                    <td v-show="args.network_cumul && !args.network_sum" class="text-end">
                        {{ args.byte ? $filters.bytes(network.bytes_sent) : $filters.bits(network.bytes_sent) }}
                    </td>
                    <td v-show="args.network_cumul && args.network_sum" class="text-end"></td>
                    <td v-show="args.network_cumul && args.network_sum" class="text-end">
                        {{ args.byte ? $filters.bytes(network.bytes_all) : $filters.bits(network.bytes_all) }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
import { store } from '../store.js';
import { bytes } from '../filters.js';

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
        view() {
            return this.data.views['network'];
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
            }).filter(network => {
                const bytesRecvRate = this.view[network.interfaceName]['bytes_recv_rate_per_sec'];
                const bytesSentRate = this.view[network.interfaceName]['bytes_sent_rate_per_sec'];
                return (!bytesRecvRate || bytesRecvRate.hidden === false) && (!bytesSentRate || bytesSentRate.hidden === false);
            });
            return orderBy(networks, ['interfaceName']);
        },
        hasNetworks() {
            return this.networks.length > 0;
        }
    },
    methods: {
        getDecoration(interfaceName, field) {
            if (this.view[interfaceName][field] == undefined) {
                return;
            }
            return this.view[interfaceName][field].decoration.toLowerCase();
        }
    }
};
</script>
