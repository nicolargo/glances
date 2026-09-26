<template>
    <section v-if="hasDisks" id="raid" class="plugin">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">RAID disks {{ disks.length }}</th>
                    <th scope="col" class="text-end">Used</th>
                    <th scope="col" class="text-end">Total</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(disk, diskId) in disks" :key="diskId">
                    <td scope="row">
                        {{ disk.type.toUpperCase() }} {{ disk.name }}
                        <div v-show="disk.degraded" class="warning">└─ Degraded mode</div>
                        <div v-show="disk.degraded">&nbsp; &nbsp;└─ {{ disk.config }}</div>
                        <div v-show="disk.inactive" class="critical">└─ Status {{ disk.status }}</div>
                        <template v-if="disk.inactive">
                            <div v-for="(component, componentId) in disk.components" :key="componentId">
                                &nbsp; &nbsp;{{
                                    componentId === disk.components.length - 1 ? '└─' : '├─'
                                }}
                                disk {{ component.number }}: {{ component.name }}
                            </div>
                        </template>
                    </td>
                    <td v-show="disk.status == 'active'" scope="row" class="text-end" :class="getAlert(disk)">
                        {{ disk.used }}
                    </td>
                    <td v-show="disk.status == 'active'" scope="row" class="text-end" :class="getAlert(disk)">
                        {{ disk.available }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy } from "lodash";

export default {
	props: {
		data: {
			type: Object,
		},
	},
	computed: {
		stats() {
			return this.data.stats["raid"];
		},
		disks() {
			const disks = Object.entries(this.stats).map(([diskKey, diskData]) => {
				const components = Object.entries(diskData.components).map(
					([name, number]) => {
						return {
							number: number,
							name: name,
						};
					},
				);
				return {
					name: diskKey,
					type: diskData.type == null ? "UNKNOWN" : diskData.type,
					used: diskData.used,
					available: diskData.available,
					status: diskData.status,
					// Mirrors RaidPlugin.raid_alert: raid0 has no redundancy, so
					// used < available carries no meaning there, and an unknown
					// device count is not a degradation. Guarding null matters in JS
					// where `null < 5` is true, which flagged an unreadable array.
					degraded:
						diskData.type !== 'raid0' &&
						diskData.used != null &&
						diskData.available != null &&
						diskData.used < diskData.available,
					config:
						diskData.config == null ? "" : diskData.config.replace("_", "A"),
					inactive: diskData.status == "inactive",
					components: orderBy(components, ["number"]),
				};
			});
			return orderBy(disks, ["name"]);
		},
		hasDisks() {
			return this.disks.length > 0;
		},
	},
	methods: {
		getAlert(disk) {
			// Same order as RaidPlugin.raid_alert on the Python side: raid0 first,
			// then inactive, then an unknown device count, then the comparison.
			if (disk.type === 'raid0') {
				return "ok";
			}
			if (disk.inactive) {
				return "critical";
			}
			if (disk.used == null || disk.available == null) {
				return "";
			}
			if (disk.used < disk.available) {
				return "warning";
			}
			return "ok";
		},
	},
};
</script>