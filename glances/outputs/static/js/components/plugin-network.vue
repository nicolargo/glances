<template>
    <section class="plugin" id="network" v-if="hasNetworks">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">NETWORK</th>
                    <th scope="col" class="text-end w-25" v-show="!args.network_cumul && !args.network_sum">Rx/s</th>
                    <th scope="col" class="text-end w-25" v-show="!args.network_cumul && !args.network_sum">Tx/s</th>
                    <th scope="col" class="text-end w-25" v-show="!args.network_cumul && args.network_sum"></th>
                    <th scope="col" class="text-end w-25" v-show="!args.network_cumul && args.network_sum">Rx+Tx/s</th>
                    <th scope="col" class="text-end w-25" v-show="args.network_cumul && !args.network_sum">Rx</th>
                    <th scope="col" class="text-end w-25" v-show="args.network_cumul && !args.network_sum">Tx</th>
                    <th scope="col" class="text-end w-25" v-show="args.network_cumul && args.network_sum"></th>
                    <th scope="col" class="text-end w-25" v-show="args.network_cumul && args.network_sum">Rx+Tx</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(network, networkId) in networks" :key="networkId">
                    <td scope="row" class="visible-lg-inline">
                        {{ network.ifname }}
                    </td>
                    <td class="text-end w-25" :class="getDecoration(network.interfaceName, 'bytes_recv_rate_per_sec')"
                        v-show="!args.network_cumul && !args.network_sum">
                        {{ args.byte ? $filters.bytes(network.bytes_recv_rate_per_sec) :
                            $filters.bits(network.bytes_recv_rate_per_sec) }}
                    </td>
                    <td class="text-end w-25" :class="getDecoration(network.interfaceName, 'bytes_sent_rate_per_sec')"
                        v-show="!args.network_cumul && !args.network_sum">
                        {{ args.byte ? $filters.bytes(network.bytes_sent_rate_per_sec) :
                            $filters.bits(network.bytes_sent_rate_per_sec) }}
                    </td>
                    <td class="text-end w-25" v-show="!args.network_cumul && args.network_sum"></td>
                    <td class="text-end w-25" v-show="!args.network_cumul && args.network_sum">
                        {{ args.byte ? $filters.bytes(network.bytes_all_rate_per_sec) :
                            $filters.bits(network.bytes_all_rate_per_sec) }}
                    </td>
                    <td class="text-end w-25" v-show="args.network_cumul && !args.network_sum">
                        {{ args.byte ? $filters.bytes(network.bytes_recv) : $filters.bits(network.bytes_recv) }}
                    </td>
                    <td class="text-end w-25" v-show="args.network_cumul && !args.network_sum">
                        {{ args.byte ? $filters.bytes(network.bytes_sent) : $filters.bits(network.bytes_sent) }}
                    </td>
                    <td class="text-end w-25" v-show="args.network_cumul && args.network_sum"></td>
                    <td class="text-end w-25" v-show="args.network_cumul && args.network_sum">
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
