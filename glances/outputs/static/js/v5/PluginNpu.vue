<template>
	<article v-show="!isHidden" class="gl-plugin" :aria-label="TITLE">
		<!-- Mirrors PluginGpu.vue, not CollectionBlock: the TUI's "header" line
		(npu/render_curses_v5.py) IS the device name, not a fixed label, so the
		<h2> stays for the whole component's life instead of disappearing once
		loaded. While loading/erroring it falls back to the fixed "NPU" label;
		once a device exists it becomes that device's name, capped with the
		same .gl-name/.gl-truncate pair the left-sidebar blocks use. -->
		<div class="gl-plugin-title">
			<h2 class="gl-header">
				<span v-if="npu" class="gl-name gl-truncate" :title="fullName">{{ fullName }}</span>
				<template v-else>{{ TITLE }}</template>
			</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else-if="npu" class="gl-stat-grid">
			<dl>
				<!-- TUI row 2: load% (or the freq% fallback) plus the right-aligned
				current/max frequency range -- two plain cells, neither carrying a
				label, so both <dt>s stay empty rather than inventing one. -->
				<dt class="gl-header"></dt>
				<dd :class="pctClass">{{ pctText }}</dd>
				<dt class="gl-header"></dt>
				<dd>{{ freqRangeText }}</dd>

				<dt class="gl-header">mem</dt>
				<dd :class="memClass">{{ memText }}</dd>

				<dt class="gl-header">temperature</dt>
				<dd :class="tempClass">{{ tempText }}</dd>
			</dl>
		</div>
	</article>
</template>

<script>
import { cellClassFor } from "./columns.js";
import { formatFixed0, formatAutoHz, toFahrenheit } from "./format.js";

const TITLE = "NPU";

export default {
	name: "PluginNpu",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: none of the four rows has a schema-resolved
		// label -- the TUI writes "mem" and "temperature" as literals.
		labels: { type: Object, default: () => ({}) },
		// `fahrenheit` (--fahrenheit) converts the temperature row, as in the
		// TUI's `view.get("fahrenheit")`.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// Payload order, though only the FIRST item is ever shown below --
		// v4 parity (npu/render_curses_v5.py:40-43): a fixture holding several
		// devices must still render exactly one.
		rows() {
			return (this.payload?.data || []).filter((item) => item && typeof item === "object");
		},
		npu() {
			return this.rows.length ? this.rows[0] : null;
		},
		isHidden() {
			return !!this.payload && this.rows.length === 0;
		},
		fullName() {
			return this.npu ? String(this.npu.name || TITLE) : TITLE;
		},
		// The pct cell's FIELD switches with `load`'s presence
		// (npu/render_curses_v5.py:71-78): the colour must come from whichever
		// field actually produced the number, `load` or the `freq` fallback --
		// never a fixed field name.
		pctField() {
			return this.npu && this.npu.load != null ? "load" : "freq";
		},
		pctClass() {
			return this.npu ? cellClassFor(this.payload, this.npu, this.pctField) : "";
		},
		pctText() {
			if (!this.npu) return "";
			if (this.npu.load != null) return `${formatFixed0(this.npu.load)}%`;
			if (this.npu.freq != null) return `${formatFixed0(this.npu.freq)}%`;
			return "N/A";
		},
		freqRangeText() {
			if (!this.npu) return "";
			return `${formatAutoHz(this.npu.freq_current)}/${formatAutoHz(this.npu.freq_max)}Hz`;
		},
		memClass() {
			return this.npu ? cellClassFor(this.payload, this.npu, "mem") : "";
		},
		memText() {
			if (!this.npu || this.npu.mem == null) return "N/A";
			return `${formatFixed0(this.npu.mem)}%`;
		},
		fahrenheit() {
			return !!this.serverArgs.fahrenheit;
		},
		tempValue() {
			if (!this.npu || this.npu.temperature == null) return null;
			return this.fahrenheit ? toFahrenheit(this.npu.temperature) : this.npu.temperature;
		},
		tempClass() {
			return this.npu ? cellClassFor(this.payload, this.npu, "temperature") : "";
		},
		tempText() {
			if (this.tempValue == null) return "N/A";
			return `${formatFixed0(this.tempValue)}${this.fahrenheit ? "F" : "C"}`;
		},
	},
};
</script>

<style scoped>
/* The TUI's header width (npu/render_curses_v5.py _HEADER_MAX). */
.gl-plugin {
	--gl-name-width: 17ch;
}
</style>
