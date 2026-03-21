<template>
	<footer id="footer" v-if="hasAlerts && !cleared">
		<div class="foot-header">
			<span class="foot-label">Alerts</span>
			<span class="foot-count">{{ alertCount }}</span>
			<button class="foot-clear" @click="clearAlerts">[ CLEAR ]</button>
		</div>
		<div class="foot-alert" v-for="(alert, idx) in alerts" :key="idx">
			<div class="foot-dot" :class="alert.dotClass"></div>
			<span class="foot-time">{{ alert.time }}</span>
			<template v-if="alert.ongoing">
				<span class="foot-ongoing" :class="alert.ongoingClass">ongoing</span>
			</template>
			<template v-else>
				<span class="foot-dur">{{ alert.duration }}</span>
			</template>
			<span class="foot-msg" :class="alert.msgClass">{{ alert.message }}</span>
		</div>
	</footer>
</template>

<script>
import { GlancesFavico } from "../services.js";

export default {
	props: { data: { type: Object } },
	data() {
		return {
			cleared: false,
		};
	},
	watch: {
		alertCount(newVal) {
			// Reset cleared state when new alerts come in
			if (newVal > 0) this.cleared = false;
			// Update favicon badge
			if (newVal > 0) {
				GlancesFavico.badge(newVal);
			} else {
				GlancesFavico.reset();
			}
		},
	},
	computed: {
		rawAlerts() {
			return this.data?.stats?.alert || [];
		},
		hasAlerts() {
			return this.rawAlerts.length > 0;
		},
		alertCount() {
			return this.rawAlerts.length;
		},
		alerts() {
			return this.rawAlerts.slice(0, 10).map(a => {
				// a = [begin_timestamp, end_timestamp, state, type, min, avg, max, top, count]
				// or  {state, type, begin, end, min, avg, max, top}
				const isArray = Array.isArray(a);
				const state = isArray ? a[2] : a.state;
				const type = isArray ? a[3] : a.type;
				const begin = isArray ? a[0] * 1000 : (a.begin || 0) * 1000;
				const end = isArray ? a[1] * 1000 : (a.end || 0) * 1000;
				const maxVal = isArray ? a[6] : a.max;
				const top = isArray ? a[7] : a.top;

				const ongoing = end === -1000 || end < 0;
				const stateLower = (state || '').toLowerCase();

				// Time display
				const beginDate = new Date(begin);
				const pad = n => String(n).padStart(2, '0');
				const time = `${pad(beginDate.getHours())}:${pad(beginDate.getMinutes())}:${pad(beginDate.getSeconds())}`;

				// Duration
				let duration = '';
				if (!ongoing && end > begin) {
					const diffSec = Math.round((end - begin) / 1000);
					const m = Math.floor(diffSec / 60);
					const s = diffSec % 60;
					duration = `${m}m${pad(s)}s`;
				}

				// Dot class
				let dotClass = 'ok';
				if (stateLower === 'critical') dotClass = 'crit';
				else if (stateLower === 'warning') dotClass = 'warn';

				// Ongoing class
				let ongoingClass = '';
				if (stateLower === 'critical') ongoingClass = 'crit';
				else if (stateLower === 'warning') ongoingClass = 'warn';

				// Message class
				let msgClass = 'info';
				if (stateLower === 'critical') msgClass = 'critical';
				else if (stateLower === 'warning') msgClass = 'warning';

				// Build message text
				let message = `${type}`;
				if (maxVal != null) message += ` (${typeof maxVal === 'number' ? maxVal.toFixed(1) : maxVal})`;
				if (top && top.length > 0) {
					const topStr = Array.isArray(top)
						? top.map(t => t.name || t).join(', ')
						: top;
					if (topStr) message += ` : ${topStr}`;
				}

				return { time, ongoing, duration, dotClass, ongoingClass, msgClass, message };
			});
		},
	},
	methods: {
		clearAlerts() {
			this.cleared = true;
			GlancesFavico.reset();
		},
	},
};
</script>
