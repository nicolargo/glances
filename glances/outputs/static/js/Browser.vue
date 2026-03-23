<template>
    <div v-if="!serversListLoaded" class="loading-page">
        Glances Central Browser is loading...
    </div>
    <main v-else style="padding:20px">
        <div v-show="servers.length == 0">
            <p style="color:var(--cyan);font-weight:700">No Glances server available</p>
            <br />
            <p>Glances servers can be defined in the glances.conf file.</p>
            <p>Glances servers can be detected automatically on the same local area network.</p>
        </div>
        <div v-show="servers.length == 1" style="color:var(--cyan);font-weight:700;margin-bottom:10px">One Glances server available</div>
        <div v-show="servers.length > 1" style="color:var(--cyan);font-weight:700;margin-bottom:10px">{{ servers.length }} Glances servers available</div>
        <table v-show="servers.length > 0" class="proc-table">
            <thead>
                <tr>
                    <th>NAME</th>
                    <th>IP</th>
                    <th>STATUS</th>
                    <th>PROTOCOL</th>
                    <th v-for="(column, columnId) in servers[0].columns" v-if="servers.length" :key="columnId">
                        {{ column.replace(/_/g, ' ').toUpperCase() }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(server, serverId) in servers" :key="serverId" style="cursor:pointer"
                    @click="goToGlances(server)">
                    <td style="color:var(--fg)">
                        {{ server.alias ? server.alias : server.name, 32 }}
                    </td>
                    <td>
                        {{ server.ip }}
                    </td>
                    <td>
                        {{ server.status }}
                    </td>
                    <td>
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
		const refreshTime = isFinite(GLANCES["refresh-time"])
			? parseInt(GLANCES["refresh-time"], 10)
			: undefined;
		this.interval = setInterval(this.updateServersList, refreshTime * 1000);
	},
	unmounted() {
		clearInterval(this.interval);
	},
	methods: {
		updateServersList() {
			fetch("api/4/serverslist", { method: "GET" })
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
			if (server.protocol === "rpc") {
				alert(
					"You just click on a Glances RPC server.\nPlease open a terminal and enter the following command line:\n\nglances -c " +
						String(server.ip) +
						" -p " +
						String(server.port),
				);
			} else {
				window.location.href =
					"http://" + String(server.name) + ":" + String(server.port);
			}
		},
		getDecoration(server, column) {
			if (server[column + "_decoration"] === undefined) {
				return;
			}
			return server[column + "_decoration"].replace("_LOG", "").toLowerCase();
		},
	},
};
</script>