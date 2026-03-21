<template>
	<main id="main">
		<!-- Containers section -->
		<template v-if="!args.disable_containers && hasContainers">
			<div class="main-section-title">Containers ({{ containers.length }})</div>
			<div class="proc-wrap" style="flex:none;max-height:120px">
				<table class="proc-table container-table">
					<thead>
						<tr>
							<th class="ct-name">Name</th>
							<th class="ct-status">Status</th>
							<th class="ct-cpu">CPU%</th>
							<th class="ct-mem">MEM</th>
							<th class="ct-cmd">Command</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="c in containers" :key="c.id">
							<td class="ct-name" style="color:var(--fg)">{{ c.name }}</td>
							<td class="ct-status" :class="c.statusClass">{{ c.status }}</td>
							<td class="ct-cpu" :class="c.cpuClass">{{ c.cpu }}</td>
							<td class="ct-mem">{{ c.mem }}</td>
							<td class="ct-cmd cmd-cell">{{ c.command }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>

		<!-- AMPs section -->
		<template v-if="!args.disable_amps && hasAmps">
			<div class="main-section-title">AMPs</div>
			<div class="amps-wrap">
				<div class="amps-row" v-for="(amp, idx) in amps" :key="idx">
					<span class="amps-name" :class="amp.deco">{{ amp.name }}</span>
					<span class="amps-count" v-if="amp.regex">{{ amp.count }}</span>
					<span class="amps-result" v-html="amp.result"></span>
				</div>
			</div>
		</template>

		<!-- Process toolbar -->
		<div class="main-toolbar">
			<div class="toolbar-left">
				<span class="toolbar-title">{{ args.programs ? 'Programs' : 'Processes' }}</span>
				<span class="toolbar-count">
					<strong>{{ processTotal }}</strong> tasks &middot;
					<strong>{{ processThread }}</strong> thr &middot;
					<strong style="color:var(--green)">{{ processRunning }}</strong> run &middot;
					<strong>{{ processSleeping }}</strong> slp
				</span>
				<span class="toolbar-sort">sorted by <span class="active">{{ sortLabel }}</span></span>
			</div>
			<div style="display:flex;gap:5px">
				<button class="t-pill" :class="{ active: isSort('io_counters') }" @click="setSort('io_counters')">IO</button>
				<button class="t-pill" :class="{ active: isSort('memory_percent') }" @click="setSort('memory_percent')">MEM</button>
				<button class="t-pill" :class="{ active: isSort('cpu_percent') }" @click="setSort('cpu_percent')">CPU &darr;</button>
				<button class="t-pill" :class="{ active: isSort(null) }" @click="setSort(null)">AUTO</button>
			</div>
		</div>

		<!-- Process table -->
		<div class="proc-wrap">
			<table class="proc-table">
				<thead>
					<tr>
						<th class="col-cpu" :class="{ 'sort-active': isSort('cpu_percent') }" @click="setSort('cpu_percent')">CPU%</th>
						<th class="col-mem" :class="{ 'sort-active': isSort('memory_percent') }" @click="setSort('memory_percent')">MEM%</th>
						<th class="col-virt">VIRT</th>
						<th class="col-res">RES</th>
						<th class="col-pid">PID</th>
						<th class="col-ni" v-if="!data.isWindows">NI</th>
						<th class="col-s">S</th>
						<th class="col-ior" :class="{ 'sort-active': isSort('io_counters') }" @click="setSort('io_counters')">IOR/s</th>
						<th class="col-iow">IOW/s</th>
						<th class="col-user" :class="{ 'sort-active': isSort('username') }" @click="setSort('username')">USER</th>
						<th class="col-time" :class="{ 'sort-active': isSort('timemillis') }" @click="setSort('timemillis')">TIME+</th>
						<th class="col-cmd" :class="{ 'sort-active': isSort('name') }" @click="setSort('name')" style="text-align:left">Command</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="proc in processList" :key="proc.pid" @click="toggleExtended(proc.pid)">
						<td :class="proc.cpuClass">
							<div class="cpu-bar-wrap">
								<span style="min-width:32px;text-align:right">{{ proc.cpu }}</span>
								<div class="cpu-ibar">
									<div class="cpu-ibar-fill" :class="proc.cpuBarClass" :style="{ width: proc.cpuBarWidth + '%' }"></div>
								</div>
							</div>
						</td>
						<td :class="proc.memClass">{{ proc.mem }}</td>
						<td>{{ proc.vms }}</td>
						<td>{{ proc.rss }}</td>
						<td style="color:var(--fg3)">{{ proc.pid }}</td>
						<td v-if="!data.isWindows" style="color:var(--fg3)">{{ proc.nice }}</td>
						<td><span class="proc-status" :class="proc.status">{{ proc.status }}</span></td>
						<td style="color:var(--fg3)">{{ proc.ioRead }}</td>
						<td style="color:var(--fg3)">{{ proc.ioWrite }}</td>
						<td style="color:var(--fg2)">{{ proc.username }}</td>
						<td style="color:var(--fg3)">{{ proc.timeStr }}</td>
						<td>
							<span class="cmd-cell" :class="proc.cmdClass" :title="proc.cmdFull">{{ proc.cmdDisplay }}</span>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</main>
</template>

<script>
import { orderBy } from "lodash";
import { store } from "../store.js";
import { GlancesHelper } from "../services.js";

const REVERSE_COLUMNS = new Set([
	'cpu_percent', 'memory_percent', 'io_counters', 'num_threads',
]);

export default {
	props: { data: { type: Object } },
	computed: {
		args() { return store.args || {}; },
		config() { return store.config || {}; },

		// ── PROCESS COUNT ──
		countStats() { return this.data?.stats?.processcount || {}; },
		processTotal() { return this.countStats.total || 0; },
		processThread() { return this.countStats.thread || 0; },
		processRunning() { return this.countStats.running || 0; },
		processSleeping() { return this.countStats.sleeping || 0; },

		// ── SORT ──
		currentSort() { return store.args?.sort_processes_key || null; },
		sortLabel() {
			const map = {
				cpu_percent: 'CPU',
				memory_percent: 'MEM',
				username: 'USER',
				name: 'NAME',
				io_counters: 'IO',
				timemillis: 'TIME',
				cpu_num: 'CORE',
			};
			return map[this.currentSort] || 'AUTO';
		},

		// ── PROCESS LIST ──
		limit() {
			const cfgMax = this.config.outputs?.max_processes_display;
			return cfgMax ? parseInt(cfgMax) : 50;
		},
		processList() {
			const isPrograms = this.args.programs;
			const rawList = isPrograms
				? this.data?.stats?.programlist || []
				: this.data?.stats?.processlist || [];
			const cores = this.data?.stats?.core?.log || 1;
			const isIrix = !this.args.disable_irix;
			const isShort = this.args.process_short_name;
			const fmt = this.$filters.bytes;
			const fmtTd = this.$filters.timedelta;

			// Sort raw data before slicing
			const sortCol = this.currentSort || 'cpu_percent';
			let sortKeys = [sortCol];
			if (sortCol === 'io_counters') {
				sortKeys = ['io_total_raw'];
			} else if (sortCol === 'timemillis') {
				sortKeys = ['cpu_times_total'];
			}
			const sortDir = REVERSE_COLUMNS.has(sortCol) ? 'desc' : 'asc';

			// Pre-compute sortable values on raw items
			const enriched = rawList.map(p => {
				const tsu = p.time_since_update || 1;
				p.io_read_raw = p.io_counters ? (p.io_counters[0] - p.io_counters[2]) / tsu : 0;
				p.io_write_raw = p.io_counters ? (p.io_counters[1] - p.io_counters[3]) / tsu : 0;
				p.io_total_raw = p.io_read_raw + p.io_write_raw;
				p.cpu_times_total = p.cpu_times
					? (p.cpu_times.user || p.cpu_times[0] || 0) + (p.cpu_times.system || p.cpu_times[1] || 0)
					: 0;
				return p;
			});

			const sorted = orderBy(enriched, sortKeys, sortKeys.map(() => sortDir));

			return sorted.slice(0, this.limit).map(p => {
				let cpuVal = p.cpu_percent || 0;
				if (!isIrix && cores > 1) {
					cpuVal = cpuVal / cores;
				}

				const cpuClass = this.getCpuClass(cpuVal);
				const cpuBarWidth = Math.min(cpuVal * 2.5, 100);
				const cpuBarClass = cpuClass || 'ok';

				const memVal = p.memory_percent || 0;
				const memClass = this.getMemClass(memVal);

				// VIRT / RES from memory_info object
				let memVirt = 0, memRes = 0;
				if (p.memory_info) {
					if (typeof p.memory_info === 'object' && !Array.isArray(p.memory_info)) {
						memVirt = p.memory_info.vms || 0;
						memRes = p.memory_info.rss || 0;
					} else if (Array.isArray(p.memory_info)) {
						memRes = p.memory_info[0] || 0;
						memVirt = p.memory_info[1] || 0;
					}
				}

				// I/O formatted
				const ioRead = fmt(Math.max(0, p.io_read_raw));
				const ioWrite = fmt(Math.max(0, p.io_write_raw));

				// Time: timedelta expects array [user, system]
				let timeStr = '?';
				if (p.cpu_times) {
					const timesArray = Array.isArray(p.cpu_times)
						? p.cpu_times
						: [p.cpu_times.user || 0, p.cpu_times.system || 0];
					const td = fmtTd(timesArray);
					if (td) {
						timeStr = String(td.hours).padStart(2, '0') + ':' +
							String(td.minutes).padStart(2, '0') + ':' +
							String(td.seconds).padStart(2, '0');
					}
				}

				// Command display
				let cmdline = p.cmdline;
				if (Array.isArray(cmdline)) {
					cmdline = cmdline.join(' ').replace(/\n/g, ' ');
				}
				const name = isShort ? (p.name || '') : (cmdline || p.name || '');
				const cmdFull = cmdline || p.name || '';

				const maxLen = 80;
				const cmdDisplay = name.length > maxLen ? name.substring(0, maxLen) + '\u2026' : name;

				const cmdClass = '';

				return {
					pid: p.pid,
					cpu: cpuVal.toFixed(1),
					cpuVal,
					cpuClass,
					cpuBarWidth,
					cpuBarClass,
					mem: memVal.toFixed(1),
					memClass,
					vms: fmt(memVirt),
					rss: fmt(memRes),
					nice: p.nice ?? '',
					status: p.status || 'S',
					ioRead,
					ioWrite,
					username: p.username || '',
					timeStr,
					cmdDisplay,
					cmdFull,
					cmdClass,
				};
			});
		},

		// ── CONTAINERS ──
		hasContainers() {
			const c = this.data?.stats?.containers;
			return c && c.length > 0;
		},
		containers() {
			const list = this.data?.stats?.containers || [];
			const fmt = this.$filters.bytes;
			return list.slice(0, 10).map(c => {
				const status = c.Status || c.status || 'unknown';
				const statusClass = status.startsWith('Up') || status === 'running' ? 'ok' : 'critical';
				return {
					id: c.Id || c.id,
					name: c.name || '',
					status,
					statusClass,
					cpu: (c.cpu?.total || 0).toFixed(1),
					cpuClass: (c.cpu?.total || 0) > 50 ? 'warning' : '',
					mem: fmt(c.memory?.usage || 0),
					command: c.Command || c.command || '',
				};
			});
		},

		// ── AMPS ──
		hasAmps() {
			const a = this.data?.stats?.amps;
			return a && a.filter(p => p.result !== null).length > 0;
		},
		amps() {
			const list = this.data?.stats?.amps || [];
			const nl2br = this.$filters.nl2br;
			return list.filter(p => p.result !== null).map(p => {
				let deco = 'ok';
				if (p.count > 0) {
					if ((p.countmin !== null && p.count < p.countmin) ||
						(p.countmax !== null && p.count > p.countmax)) {
						deco = 'careful';
					}
				} else {
					deco = p.countmin === null ? 'ok' : 'critical';
				}
				return {
					name: p.name,
					count: p.count,
					regex: p.regex,
					result: nl2br(p.result),
					deco,
				};
			});
		},
	},
	methods: {
		isSort(key) {
			return this.currentSort === key;
		},
		setSort(key) {
			store.args.sort_processes_key = key;
		},
		toggleExtended(pid) {
			fetch(`api/4/processes/extended/${pid}`, { method: 'POST' });
		},
		getCpuClass(val) {
			const alert = GlancesHelper.getAlert('processlist', 'processlist_cpu_', val, 100);
			return alert || '';
		},
		getMemClass(val) {
			const alert = GlancesHelper.getAlert('processlist', 'processlist_mem_', val, 100);
			return alert || '';
		},
	},
};
</script>
