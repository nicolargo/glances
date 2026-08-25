<template>
    <section id="percpu" class="plugin">
        <!-- d-none d-xl-block d-xxl-block -->
        <div class="table-responsive">
            <table class="table-sm table-borderless">
                <thead>
                    <tr>
                        <th v-if="args.disable_quicklook" scope="col">CPU</th>
                        <td v-if="args.disable_quicklook" scope="col">total</td>
                        <td scope="col">user</td>
                        <td scope="col">system</td>
                        <td v-show="hasStat('idle')" scope="col">idle</td>
                        <td v-show="hasStat('iowait')" scope="col">iowait</td>
                        <td v-show="hasStat('steal')" scope="col">steal</td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(percpu, percpuId) in percpuStats" :key="percpuId">
                        <td v-if="args.disable_quicklook" scope="col">CPU{{ percpu.cpu_number }}</td>
                        <td v-if="args.disable_quicklook" scope="col">{{ percpu.total }}%</td>
                        <td scope="col" :class="getUserAlert(percpu)">{{ percpu.user }}%</td>
                        <td scope="col" :class="getSystemAlert(percpu)">{{ percpu.system }}%</td>
                        <td v-show="hasStat('idle')" scope="col">{{ percpu.idle }}%</td>
                        <td v-show="hasStat('iowait')" scope="col" :class="getIOWaitAlert(percpu)">{{
                            percpu.iowait }}%</td>
                        <td v-show="hasStat('steal')" scope="col">{{ percpu.steal }}%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
</template>

<script>
import { chunk } from "lodash";
import { GlancesHelper } from "../services.js";
import { store } from "../store.js";

export default {
	props: {
		data: {
			type: Object,
		},
	},
	data() {
		return {
			store,
		};
	},
	computed: {
		args() {
			return this.store.args || {};
		},
		config() {
			return this.store.config || {};
		},
		percpuStats() {
			return this.data.stats["percpu"];
		},
	},
	methods: {
		// psutil reports a different set of CPU times per OS: no iowait or steal
		// on Windows and macOS, no dpc/interrupt on Linux. Gating the header on
		// the same answer as the value keeps the two in step -- and asking the
		// whole table rather than one row keeps every row the same width.
		hasStat(name) {
			return (this.percpuStats || []).some((cpu) => cpu[name] != undefined);
		},
		getUserAlert(cpu) {
			return GlancesHelper.getAlert("percpu", "percpu_user_", cpu.user);
		},
		getSystemAlert(cpu) {
			return GlancesHelper.getAlert("percpu", "percpu_system_", cpu.system);
		},
		getIOWaitAlert(cpu) {
			return GlancesHelper.getAlert("percpu", "percpu_iowait_", cpu.iowait);
		},
	},
};
</script>