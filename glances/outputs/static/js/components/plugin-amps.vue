<template>
    <section v-if="hasAmps" id="amps" class="plugin">
        <table class="table table-sm table-borderless">
            <tbody>
                <tr v-for="(process, processId) in processes" :key="processId">
                    <td :class="getNameDecoration(process)">{{ process.name }}</td>
                    <td v-if="process.regex">{{ process.count }}</td>
                    <td class="process-result" v-html="$filters.nl2br(process.result)"></td>
                </tr>
            </tbody>
        </table>

        <!-- <div class="table">
            <div class="table-row" v-for="(process, processId) in processes" :key="processId">
                <div class="table-cell text-start" :class="getNameDecoration(process)">
                    {{ process.name }}
                </div>
                <div class="table-cell text-start" v-if="process.regex">{{ process.count }}</div>
                <div
                    class="table-cell text-start process-result"
                    v-html="$filters.nl2br(process.result)"
                ></div>
            </div>
        </div> -->

    </section>
</template>

<script>
export default {
	props: {
		data: {
			type: Object,
		},
	},
	computed: {
		stats() {
			return this.data.stats["amps"];
		},
		processes() {
			return this.stats.filter((process) => process.result !== null);
		},
		hasAmps() {
			return this.processes.length > 0;
		},
	},
	methods: {
		// Mirrors AmpsPlugin.get_alert() in glances/plugins/amps/__init__.py,
		// which is the authority: an unset bound defaults to the observed count,
		// an out-of-range count is WARNING (not CAREFUL), and a configured
		// minimum of 0 means a count of 0 is fine.
		getNameDecoration(process) {
			const count = process.count;
			const countMin = process.countmin;
			const countMax = process.countmax;

			if (count > 0) {
				const min = countMin === null ? count : Number(countMin);
				const max = countMax === null ? count : Number(countMax);
				return min <= count && count <= max ? "ok" : "warning";
			}

			return countMin === null || Number(countMin) === 0 ? "ok" : "critical";
		},
	},
};
</script>