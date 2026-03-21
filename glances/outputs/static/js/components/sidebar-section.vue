<template>
	<aside id="sidebar">

		<!-- NETWORK -->
		<div class="sb-section" v-if="!args.disable_network && hasNetworks">
			<div class="sb-title">Network <span class="sub">Rx / Tx</span></div>
			<div class="sb-row" v-for="net in networks" :key="net.ifname">
				<span class="name">{{ net.alias || net.ifname }}</span>
				<span class="vals">
					<span class="v" :class="net.rxDeco">{{ net.rx }}</span>
					<span class="dim">/</span>
					<span class="v" :class="net.txDeco">{{ net.tx }}</span>
				</span>
			</div>
		</div>

		<!-- PORTS -->
		<div class="sb-section" v-if="!args.disable_ports && hasPorts">
			<template v-for="port in ports" :key="port.id">
				<div class="sb-row">
					<span class="name">{{ port.description || port.host }}</span>
					<span class="vals">
						<span class="v" :class="port.deco">{{ port.display }}</span>
					</span>
				</div>
			</template>
		</div>

		<!-- WIFI -->
		<div class="sb-section" v-if="!args.disable_wifi && hasWifi">
			<template v-for="ap in wifiList" :key="ap.ssid">
				<div class="sb-row">
					<span class="name">{{ ap.ssid }}</span>
					<span class="vals">
						<span class="v" :class="ap.deco">{{ ap.signal }} dBm</span>
					</span>
				</div>
			</template>
		</div>

		<!-- DISK I/O -->
		<div class="sb-section" v-if="!args.disable_diskio && hasDisks">
			<div class="sb-title">Disk I/O <span class="sub">R / W</span></div>
			<div class="sb-row" v-for="disk in disks" :key="disk.name">
				<span class="name">{{ disk.alias || disk.name }}</span>
				<span class="vals">
					<span class="v" :class="disk.rDeco">{{ disk.read }}</span>
					<span class="dim">/</span>
					<span class="v" :class="disk.wDeco">{{ disk.write }}</span>
				</span>
			</div>
		</div>

		<!-- FILESYSTEM -->
		<div class="sb-section" v-if="!args.disable_fs && hasFs">
			<div class="sb-title">Filesystem <span class="sub">Used / Total</span></div>
			<div class="sb-row" v-for="fs in fileSystems" :key="fs.mnt">
				<span class="name">{{ fs.alias || fs.name }}</span>
				<span class="vals">
					<div class="sb-minibar">
						<div class="sb-minibar-fill" :class="fs.deco" :style="{ width: fs.percent + '%' }"></div>
					</div>
					<span class="v" :class="fs.deco">{{ fs.used }}/{{ fs.size }}</span>
				</span>
			</div>
		</div>

		<!-- FOLDERS -->
		<div class="sb-section" v-if="hasFolders">
			<div class="sb-title">Folders <span class="sub">Size</span></div>
			<div class="sb-row" v-for="folder in folders" :key="folder.path">
				<span class="name" style="font-size:10px">{{ folder.path }}</span>
				<span class="vals">
					<span class="v" :class="folder.deco">{{ folder.size }}</span>
				</span>
			</div>
		</div>

		<!-- SENSORS -->
		<div class="sb-section" v-if="!args.disable_sensors && hasSensors">
			<div class="sb-title">Sensors</div>
			<div class="sb-row" v-for="sensor in sensors" :key="sensor.label">
				<span class="name">{{ sensor.label }}</span>
				<span class="vals">
					<template v-if="sensor.type === 'temperature_core' || sensor.type === 'temperature_hdd' || sensor.type === 'battery'">
						<div class="sb-minibar">
							<div class="sb-minibar-fill" :class="sensor.deco" :style="{ width: sensor.barPercent + '%' }"></div>
						</div>
					</template>
					<span class="v" :class="sensor.deco">{{ sensor.display }}</span>
				</span>
			</div>
		</div>

		<!-- CONNECTIONS -->
		<div class="sb-section" v-if="!args.disable_connections && hasConnections" style="border-bottom:none">
			<div class="sb-title">Connections</div>
			<div class="sb-row" v-if="connections.listen != null">
				<span class="name">Listen</span>
				<span class="vals"><span class="v neutral">{{ connections.listen }}</span></span>
			</div>
			<div class="sb-row" v-if="connections.initiated != null">
				<span class="name">Initiated</span>
				<span class="vals"><span class="v neutral">{{ connections.initiated }}</span></span>
			</div>
			<div class="sb-row" v-if="connections.established != null">
				<span class="name">Established</span>
				<span class="vals"><span class="v neutral">{{ connections.established }}</span></span>
			</div>
			<div class="sb-row" v-if="connections.terminated != null">
				<span class="name">Terminated</span>
				<span class="vals"><span class="v neutral">{{ connections.terminated }}</span></span>
			</div>
			<div class="sb-row" v-if="connections.tracked != null">
				<span class="name">Tracked</span>
				<span class="vals"><span class="v" :class="connections.trackedDeco">{{ connections.tracked }}</span></span>
			</div>
		</div>

	</aside>
</template>

<script>
import { orderBy } from "lodash";
import { store } from "../store.js";

export default {
	props: { data: { type: Object } },
	computed: {
		args() { return store.args || {}; },

		// ── NETWORK ──
		hasNetworks() {
			const nets = this.data?.stats?.network;
			return nets && nets.length > 0;
		},
		networks() {
			const nets = this.data?.stats?.network || [];
			const views = this.data?.views?.network || {};
			const isByte = store.args?.byte;
			const isCumul = store.args?.network_cumul;
			const isSum = store.args?.network_sum;
			const fmt = this.$filters.bytes;
			const fmtBits = this.$filters.bits;

			return nets
				.filter(n => !n.is_up || n.is_up !== false)
				.map(n => {
					const name = n.interface_name;
					let rx, tx, rxDeco = 'neutral', txDeco = 'neutral';

					if (isSum) {
						const val = isCumul ? n.bytes_all : n.bytes_all_rate_per_sec;
						rx = isByte ? fmt(val) : fmtBits(val);
						tx = '';
					} else if (isCumul) {
						rx = isByte ? fmt(n.bytes_recv) : fmtBits(n.bytes_recv);
						tx = isByte ? fmt(n.bytes_sent) : fmtBits(n.bytes_sent);
					} else {
						rx = isByte ? fmt(n.bytes_recv_rate_per_sec) : fmtBits(n.bytes_recv_rate_per_sec);
						tx = isByte ? fmt(n.bytes_sent_rate_per_sec) : fmtBits(n.bytes_sent_rate_per_sec);
					}

					if (views[name]) {
						if (views[name].bytes_recv_rate_per_sec?.decoration)
							rxDeco = views[name].bytes_recv_rate_per_sec.decoration.toLowerCase();
						if (views[name].bytes_sent_rate_per_sec?.decoration)
							txDeco = views[name].bytes_sent_rate_per_sec.decoration.toLowerCase();
					}

					return { ifname: name, alias: n.alias, rx, tx, rxDeco, txDeco };
				});
		},

		// ── PORTS ──
		hasPorts() {
			const p = this.data?.stats?.ports;
			return p && p.length > 0;
		},
		ports() {
			const ports = this.data?.stats?.ports || [];
			return ports.map((p, i) => {
				let display, deco;
				if (p.port != null) {
					// TCP port — status is RTT in seconds, convert to ms
					if (p.status === null) { deco = 'careful'; display = '?'; }
					else if (p.status === false) { deco = 'critical'; display = 'Timeout'; }
					else if (p.rtt_warning && p.status > p.rtt_warning) { deco = 'warning'; display = (p.status * 1000).toFixed(0) + 'ms'; }
					else { deco = 'ok'; display = (p.status * 1000).toFixed(0) + 'ms'; }
				} else if (p.url != null) {
					// Web URL
					if (p.status === null) { deco = 'careful'; display = '?'; }
					else if (![200, 301, 302].includes(p.status)) { deco = 'critical'; display = p.status; }
					else if (p.rtt_warning && p.elapsed > p.rtt_warning) { deco = 'warning'; display = p.elapsed?.toFixed(0) + 'ms'; }
					else { deco = 'ok'; display = p.status; }
				} else {
					return null;
				}
				return { id: i, description: p.description || p.host || p.url, display, deco };
			}).filter(Boolean);
		},

		// ── WIFI ──
		hasWifi() {
			const w = this.data?.stats?.wifi;
			return w && w.length > 0;
		},
		wifiList() {
			const w = this.data?.stats?.wifi || [];
			const views = this.data?.views?.wifi || {};
			return w.filter(h => h.ssid).map(h => {
				let deco = 'default';
				if (views[h.ssid]?.quality_level?.decoration) {
					deco = views[h.ssid].quality_level.decoration.toLowerCase();
				}
				return {
					ssid: h.ssid,
					signal: h.quality_level,
					deco,
				};
			});
		},

		// ── DISK I/O ──
		hasDisks() {
			const d = this.data?.stats?.diskio;
			return d && d.length > 0;
		},
		disks() {
			const disks = this.data?.stats?.diskio || [];
			const views = this.data?.views?.diskio || {};
			const fmt = this.$filters.bytes;
			const isIops = store.args?.diskio_iops;
			const isLatency = store.args?.diskio_latency;

			return disks.map(d => {
				const name = d.disk_name;
				let read, write;
				if (isLatency) {
					read = (d.read_latency || 0).toFixed(1) + 'ms';
					write = (d.write_latency || 0).toFixed(1) + 'ms';
				} else if (isIops) {
					read = Math.round(d.read_count_rate_per_sec || 0).toString();
					write = Math.round(d.write_count_rate_per_sec || 0).toString();
				} else {
					read = fmt(d.read_bytes_rate_per_sec);
					write = fmt(d.write_bytes_rate_per_sec);
				}

				let rDeco = 'neutral', wDeco = 'neutral';
				if (views[name]) {
					if (views[name].read_bytes_rate_per_sec?.decoration)
						rDeco = views[name].read_bytes_rate_per_sec.decoration.toLowerCase();
					if (views[name].write_bytes_rate_per_sec?.decoration)
						wDeco = views[name].write_bytes_rate_per_sec.decoration.toLowerCase();
				}

				return { name, alias: d.alias, read, write, rDeco, wDeco };
			});
		},

		// ── FILESYSTEM ──
		hasFs() {
			const f = this.data?.stats?.fs;
			return f && f.length > 0;
		},
		fileSystems() {
			const fsList = this.data?.stats?.fs || [];
			const views = this.data?.views?.fs || {};
			const fmt = this.$filters.bytes;

			return fsList.map(f => {
				const mnt = f.mnt_point;
				let deco = 'default';
				if (views[mnt]?.used?.decoration) {
					const d = views[mnt].used.decoration.toLowerCase();
					deco = (d === 'default') ? 'default' : d;
				}
				const alias = f.alias || (mnt === '/' ? 'Root' : mnt.split('/').pop() || mnt);
				return {
					mnt,
					name: alias,
					alias: f.alias,
					percent: f.percent || 0,
					used: fmt(f.used),
					size: fmt(f.size),
					deco,
				};
			});
		},

		// ── FOLDERS ──
		hasFolders() {
			const f = this.data?.stats?.folders;
			return f && f.length > 0;
		},
		folders() {
			const folders = this.data?.stats?.folders || [];
			const fmt = this.$filters.bytes;

			return folders.map(f => {
				let deco = 'ok';
				if (f.errno && f.errno > 0) {
					deco = 'critical';
				} else if (f.critical && f.size > f.critical * 1000000) {
					deco = 'critical';
				} else if (f.warning && f.size > f.warning * 1000000) {
					deco = 'warning';
				} else if (f.careful && f.size > f.careful * 1000000) {
					deco = 'careful';
				}

				return {
					path: f.path,
					size: f.errno && f.errno > 0 ? '? ' + f.errno : fmt(f.size),
					deco,
				};
			});
		},

		// ── SENSORS ──
		hasSensors() {
			const s = this.data?.stats?.sensors;
			return s && s.length > 0;
		},
		sensors() {
			const sensors = this.data?.stats?.sensors || [];
			const views = this.data?.views?.sensors || {};
			const isFahrenheit = store.args?.fahrenheit;

			return sensors.map(s => {
				let value = s.value;
				let unit = s.unit || '';

				if (isFahrenheit && (s.type === 'temperature_core' || s.type === 'temperature_hdd')) {
					value = value * 1.8 + 32;
					unit = '\u00b0F';
				}

				let deco = 'neutral';
				if (views[s.label]?.value?.decoration) {
					deco = views[s.label].value.decoration.toLowerCase();
				}

				let barPercent = 0;
				if (s.type === 'battery') {
					barPercent = value;
				} else if (s.type === 'temperature_core' || s.type === 'temperature_hdd') {
					barPercent = Math.min(100, (value / 100) * 100);
				}

				const display = typeof value === 'number'
					? value.toFixed(0) + unit
					: value + unit;

				return { label: s.label, type: s.type, display, deco, barPercent };
			});
		},

		// ── CONNECTIONS ──
		hasConnections() {
			return this.data?.stats?.connections != null;
		},
		connections() {
			const c = this.data?.stats?.connections || {};
			const views = this.data?.views?.connections || {};
			let trackedDeco = 'neutral';
			if (views.nf_conntrack_percent?.decoration) {
				trackedDeco = views.nf_conntrack_percent.decoration.toLowerCase();
			}
			const tracked = c.nf_conntrack_count != null && c.nf_conntrack_max
				? `${c.nf_conntrack_count}/${c.nf_conntrack_max}`
				: null;

			return {
				listen: c.LISTEN,
				initiated: c.initiated,
				established: c.ESTABLISHED,
				terminated: c.terminated,
				tracked,
				trackedDeco,
			};
		},
	},
};
</script>
