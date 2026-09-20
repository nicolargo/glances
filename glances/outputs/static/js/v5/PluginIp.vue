<template>
	<span v-show="error || address || publicAddress" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<template v-if="address">
				<span class="gl-header">IP</span>
				<span>{{ privateText }}</span>
			</template>
			<template v-if="publicAddress">
				<span class="gl-header">Pub</span>
				<span>{{ publicShown }}</span>
				<!--
					`title` carries the geolocation string ONLY. Never the public
					address: a hover would bypass --hide-public-info.
				-->
				<span v-if="publicInfo" class="gl-truncate" :title="publicInfo">{{ publicInfo }}</span>
			</template>
		</template>
	</span>
</template>

<script>
import { PLUGIN_PROPS } from "./plugin_props.js";
// glances/plugins/ip/render_curses_v5.py:35-37 -- a.b.c.d -> a.b.*.*
function hideIp(ip) {
	return `${String(ip).split(".").slice(0, 2).join(".")}.*.*`;
}

export default {
	name: "PluginIp",
	// Reads `serverArgs.hide_public_info` (--hide-public-info) and
	// `degrade.hide_ip_location`, both in `publicInfo` below.
	props: { ...PLUGIN_PROPS },
	computed: {
		// Mirrors glances/plugins/ip/render_curses_v5.py: the private cells
		// need `address`, the public cells need `public_address`, and a block
		// with no cell at all is not rendered. "IP" and "Pub" are block tags,
		// not field labels (spec §7.3).
		address() {
			return this.payload?.address || "";
		},
		privateText() {
			const cidr = this.payload?.mask_cidr;
			return cidr === null || cidr === undefined ? String(this.address) : `${this.address}/${cidr}`;
		},
		publicAddress() {
			return this.payload?.public_address || "";
		},
		// DISPLAY-ONLY masking, exactly like the TUI. /api/5/ip and /api/5/all
		// still serve the address in clear -- spec §11 tracks that; do not
		// mistake this for a privacy control.
		publicShown() {
			return this.serverArgs.hide_public_info ? hideIp(this.publicAddress) : String(this.publicAddress);
		},
		// `hide_ip_location` is the TUI's header step (1)
		// (glances_curses_v5.py:87): the widest, least essential segment of the
		// banner goes first, and both addresses survive it. spec D3 said the
		// browser would not reproduce this; the 2026-09-12 spec reverses that.
		publicInfo() {
			if (this.degrade.hide_ip_location) return "";
			return this.payload?.public_info_human || "";
		},
	},
};
</script>
