<template>
	<header id="header">
		<!-- System: hostname / OS -->
		<div class="hdr-system">
			<div class="hdr-hostname" :class="{ disconnected: isDisconnected }">
				<template v-if="isDisconnected">Disconnected from </template>{{ hostname }}
			</div>
			<div class="hdr-os">{{ humanReadableName }}</div>
		</div>

		<!-- Right side blocks -->
		<div class="hdr-right">
			<!-- IP block -->
			<div class="hdr-block" v-if="hasIp">
				<div class="hdr-ip-row">
					<span class="hdr-ip-label">LOCAL</span>
					<span class="hdr-ip-val private">{{ address }}{{ maskCidr ? '/' + maskCidr : '' }}</span>
				</div>
				<div class="hdr-ip-row">
					<span class="hdr-ip-label">PUBLIC</span>
					<span class="hdr-ip-val">{{ publicAddress }}</span>
					<span class="hdr-ip-location" v-if="publicInfo">&mdash; {{ publicInfo }}</span>
				</div>
			</div>

			<!-- Uptime + clock block -->
			<div class="hdr-block hdr-block--right">
				<div>
					<span class="pulse-dot" :class="{ disconnected: isDisconnected }"></span>
					<span class="hdr-uptime">&uarr; {{ uptime }}</span>
				</div>
				<div class="hdr-clock">{{ clock }}</div>
			</div>
		</div>
	</header>
</template>

<script>
import { store } from "../store.js";

export default {
	props: {
		data: { type: Object },
	},
	data() {
		return {
			clock: '',
			clockInterval: null,
		};
	},
	computed: {
		stats() { return this.data.stats || {}; },
		isDisconnected() { return store.status === 'FAILURE'; },
		hostname() { return this.stats.system?.hostname || ''; },
		humanReadableName() { return this.stats.system?.hr_name || ''; },
		hasIp() { return this.stats.ip && this.stats.ip.address; },
		address() { return this.stats.ip?.address || ''; },
		maskCidr() { return this.stats.ip?.mask_cidr || ''; },
		publicAddress() { return this.stats.ip?.public_address || ''; },
		publicInfo() { return this.stats.ip?.public_info_human || ''; },
		uptime() { return this.stats.uptime || ''; },
	},
	mounted() {
		this.updateClock();
		this.clockInterval = setInterval(() => this.updateClock(), 1000);
	},
	beforeUnmount() {
		if (this.clockInterval) clearInterval(this.clockInterval);
	},
	methods: {
		updateClock() {
			if (this.stats.now?.custom) {
				this.clock = this.stats.now.custom;
			} else {
				const n = new Date();
				const p = x => String(x).padStart(2, '0');
				this.clock = `${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())} ${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
			}
		},
	},
};
</script>
