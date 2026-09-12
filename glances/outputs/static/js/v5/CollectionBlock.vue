<template>
	<article v-show="!hidden" class="gl-plugin" :aria-label="title">
		<!-- Keep every comment INSIDE this root: the build keeps template
		comments, and one before <article> would make a second root node, which
		drops the `data-plugin` and `aria-label` attributes AppShell passes down
		(they now cascade through two component roots -- this one and the
		plugin's). Pinned by test_every_collection_block_keeps_its_root_attributes. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">{{ title }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<!-- G9-6 D6: a loaded collection's title is its first <th>, so the
			<h2> above renders only while loading or erroring. G9-7 D4: a block
			with no header row in the TUI (`ports`) passes no #head slot and gets
			no <thead> at all. -->
			<thead v-if="$slots.head">
				<slot name="head"></slot>
			</thead>
			<slot name="body"></slot>
		</table>
	</article>
</template>

<script>
export default {
	name: "CollectionBlock",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		title: { type: String, required: true },
		// Hide the whole block. Five of the six G9-7 blocks (ports, folders,
		// irq, raid, smart) pass `!!payload && rows.length === 0`, because their
		// TUI renderers return [] on an empty collection; `connections` is the
		// sixth but is scalar and never uses this shell. The five G9-6 blocks
		// (network, wifi, diskio, fs, sensors) do not pass it at all: their TUI
		// renderers still paint a header row for an empty collection, so the
		// shell's default `false` keeps the WebUI matching them.
		hidden: { type: Boolean, default: false },
	},
};
</script>
