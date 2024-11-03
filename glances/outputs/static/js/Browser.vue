<template>
    <div v-if="!serversListLoaded" class="container-fluid" id="loading-page">
        <div class="loader">Glances Central Browser is loading...</div>
    </div>
    <main v-else>
        <p>{{ servers }}</p>
        <table class="table table-sm table-borderless margin-bottom table-hover">
            <thead>
                <tr>
                    <th scope="col">NAME</th>
                    <th scope="col" class="">IP</th>
                    <th scope="col" class="">STATUS</th>
                    <th scope="col" class="">PROTOCOL</th>
                    <th v-if="servers.length" v-for="(column, columnId) in servers[0].columns" :key="columnId">
                        {{ column.replace(/_/g, ' ').toUpperCase() }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(server, serverId) in servers" :key="serverId" @click="goToGlances(server.uri)"
                    style="cursor: pointer">
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
                    <td v-if="servers.length" v-for="(column, columnId) in server.columns" :key="columnId">
                        {{ formatNumber(server[column]) }}
                    </td>
                </tr>
            </tbody>
        </table>
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
        goToGlances(uri) {
            window.location.href = uri;
        }
    },
    computed: {
        serversListLoaded() {
            return this.servers !== undefined;
        },
    },
    destroyed() {
        clearInterval(this.interval)
    }
};
</script>