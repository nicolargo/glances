<template>
    <div v-if="!serversListLoaded" id="loading-page" class="container-fluid">
        <div class="loader">Glances Central Browser is loading...</div>
    </div>
    <main v-else>
        <span v-show="servers.length == 0">
            <p class="title">No Glances server available</p>
            <br />
            <p>Glances servers can be defined in the glances.conf file.</p>
            <p>Glances servers can be detected automaticaly on the same local area network.</p>
        </span>
        <span v-show="servers.length == 1" class="title">One Glances server available</span>
        <span v-show="servers.length > 1" class="title"> {{ servers.length }} Glances servers available</span>
        <table v-show="servers.length > 0" class="table table-sm table-borderless margin-bottom table-hover">
            <thead>
                <tr>
                    <th scope="col">NAME</th>
                    <th scope="col" class="">IP</th>
                    <th scope="col" class="">STATUS</th>
                    <th scope="col" class="">PROTOCOL</th>
                    <th v-for="(column, columnId) in servers[0].columns" v-if="servers.length" :key="columnId">
                        {{ column.replace(/_/g, ' ').toUpperCase() }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(server, serverId) in servers" :key="serverId" style="cursor: pointer"
                    @click="goToGlances(server)">
                    <td scope=" row">
                        {{ server.alias ? server.alias : server.name, 32 }}
                    </td>
                    <td class="">
                        {{ server.ip }}
                    </td>
                    <td class="">
                        {{ server.status }}
                    </td>
                    <td class="">
                        {{ server.protocol }}
                    </td>
                    <td v-for="(column, columnId) in server.columns" v-if="servers.length" :key="columnId"
                        :class="getDecoration(server, column)">
                        {{ formatNumber(server[column]) }}
                    </td>
                </tr>
            </tbody>
        </table>
        <!-- DEBUGGING -->
        <!-- <p>{{ servers }}</p> -->
    </main>
</template>

<script>
// import hotkeys from 'hotkeys-js';
// import { GlancesStats } from './services.js';
// import { store } from './store.js';

export default {
    data() {
        return {
            servers: undefined,
        };
    },
    computed: {
        serversListLoaded() {
            return this.servers !== undefined;
        },
    },
    created() {
        this.updateServersList();
    },
    mounted() {
        const GLANCES = window.__GLANCES__ || {};
        const refreshTime = isFinite(GLANCES['refresh-time'])
            ? parseInt(GLANCES['refresh-time'], 10)
            : undefined;
        this.interval = setInterval(this.updateServersList, refreshTime * 1000)
    },
    unmounted() {
        clearInterval(this.interval)
    },
    methods: {
        updateServersList() {
            fetch('api/4/serverslist', { method: 'GET' })
                .then((response) => response.json())
                .then((response) => (this.servers = response));
        },
        formatNumber(value) {
            if (typeof value === "number" && !isNaN(value)) {
                return value.toFixed(1);
            }
            return value;
        },
        goToGlances(server) {
            if (server.protocol === 'rpc') {
                alert("You just click on a Glances RPC server.\nPlease open a terminal and enter the following command line:\n\nglances -c " + String(server.ip) + " -p " + String(server.port))
            } else {
                window.location.href = server.uri;
            }
        },
        getDecoration(server, column) {
            if (server[column + '_decoration'] === undefined) {
                return;
            }
            return server[column + '_decoration'].replace('_LOG', '').toLowerCase();
        }
    }
};
</script>