<template>
	<main class="gl-browser">
		<p v-if="servers === null" class="gl-muted">loading…</p>
		<template v-else>
			<h1 class="gl-browser-title gl-strong">{{ title(servers.length) }}</h1>
			<p class="gl-browser-counts">
				<span v-for="item in statusCounts(servers)" :key="item.status" :class="statusClass(item.status)">
					{{ item.status }}: {{ item.count }}
				</span>
				<span v-if="error" class="gl-level-critical">{{ error }}</span>
			</p>
			<p v-if="servers.length === 0" class="gl-muted">
				Servers come from [serverlist] in glances.conf, and from the LAN (Zeroconf).
			</p>
			<table v-else class="gl-table gl-browser-table">
				<thead>
					<tr>
						<th></th>
						<th></th>
						<th v-for="label in labels" :key="`p-${label}`" class="gl-header">{{ headerRows(label)[0] }}</th>
					</tr>
					<tr>
						<th class="gl-header">NAME</th>
						<th class="gl-header">STATUS</th>
						<th v-for="label in labels" :key="`f-${label}`" class="gl-header">{{ headerRows(label)[1] }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="server in servers"
						:key="`${server.source}:${server.name}:${server.port}`"
						:class="{ 'gl-browser-link': hrefOf(server) }"
						@click="open(server)"
					>
						<td>
							<a v-if="hrefOf(server)" :href="hrefOf(server)" @click.stop>{{ displayName(server) }}</a>
							<span v-else>{{ displayName(server) }}</span>
						</td>
						<td :class="statusClass(server.status)">{{ server.status }}</td>
						<td v-for="label in labels" :key="label">
							<span :class="cellClass(server.columns[label])">{{ formatCell(server.columns[label]) }}</span>
						</td>
					</tr>
				</tbody>
			</table>
		</template>
	</main>
</template>

<script>
// The Web UI browser page (P3-6): /api/5/serverslist, polled at
// `[global] refresh`, in the WebUI's tokens. Served at /browser by
// `glances-v5 -s --browser`. A click opens the server's own Web UI.
import { getJson, resolveConfig } from "./api.js";
import {
	cellClass,
	columnLabels,
	displayName,
	formatCell,
	headerRows,
	serverHref,
	statusClass,
	statusCounts,
	title,
} from "./browser.js";

export default {
	data() {
		return { servers: null, error: null, timer: null };
	},
	computed: {
		labels() {
			return columnLabels(this.servers || []);
		},
	},
	async mounted() {
		const { refreshSeconds, theme } = await resolveConfig();
		document.documentElement.dataset.theme = theme;
		await this.tick();
		this.timer = setInterval(() => this.tick(), refreshSeconds * 1000);
	},
	unmounted() {
		clearInterval(this.timer);
	},
	methods: {
		cellClass,
		displayName,
		formatCell,
		headerRows,
		statusClass,
		statusCounts,
		title,
		hrefOf: serverHref,
		async tick() {
			try {
				const servers = await getJson("api/5/serverslist");
				if (!Array.isArray(servers)) throw new Error("api/5/serverslist: not a list");
				this.servers = servers;
				this.error = null;
			} catch (e) {
				// Keep the last list on screen, as the TUI client does when
				// its server goes away, and say why it is not refreshing.
				if (this.servers === null) this.servers = [];
				this.error = e.message;
			}
		},
		open(server) {
			const href = serverHref(server);
			if (href) window.location.href = href;
		},
	},
};
</script>

<style>
.gl-browser {
	padding: var(--gl-gap) calc(var(--gl-gap) * 2);
}
.gl-browser-title {
	margin: 0;
	font-size: var(--gl-size-lg);
}
.gl-browser-counts {
	display: flex;
	gap: calc(var(--gl-gap) * 2);
	margin: 0 0 var(--gl-gap);
}
/* The TUI browser's table: every column left-aligned and as wide as its
 * content, two characters apart. `.gl-table` fills its slot on the main page,
 * which here would spread a few short columns across the whole window. */
.gl-browser-table {
	width: auto;
}
.gl-browser-table th,
.gl-browser-table td {
	padding-right: calc(var(--gl-col) * 3);
	white-space: nowrap;
}
.gl-browser-table a {
	color: inherit;
}
/* A row that opens a server: the process list's hover token, and only on
 * rows that actually go somewhere. */
.gl-browser-table tr.gl-browser-link {
	cursor: pointer;
}
.gl-browser-table tr.gl-browser-link:hover {
	background: var(--gl-row-hover);
}
</style>
