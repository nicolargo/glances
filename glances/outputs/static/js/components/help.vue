<template>
	<div class="help-screen" v-if="help">
		<h2>{{ help.version }} {{ help.psutil_version }}</h2>
		<p style="color:var(--fg2);margin-bottom:12px">{{ help.configuration_file }}</p>
		<table>
			<thead>
				<tr>
					<th>{{ help.header_sort.replace(':', '') }}</th>
					<th>{{ help.header_show_hide.replace(':', '') }}</th>
					<th>{{ help.header_toggle.replace(':', '') }}</th>
					<th>{{ help.header_miscellaneous.replace(':', '') }}</th>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td>{{ help.sort_auto }}</td>
					<td>{{ help.show_hide_application_monitoring }}</td>
					<td>{{ help.toggle_bits_bytes }}</td>
					<td>{{ help.misc_erase_process_filter }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_cpu }}</td>
					<td>{{ help.show_hide_diskio }}</td>
					<td>{{ help.toggle_count_rate }}</td>
					<td>{{ help.misc_generate_history_graphs }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_io_rate }}</td>
					<td>{{ help.show_hide_containers }}</td>
					<td>{{ help.toggle_used_free }}</td>
					<td>{{ help.misc_help }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_cpu_num }}</td>
					<td>{{ help.show_hide_top_extended_stats }}</td>
					<td>{{ help.toggle_bar_sparkline }}</td>
					<td>{{ help.misc_accumulate_processes_by_program }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_mem }}</td>
					<td>{{ help.show_hide_filesystem }}</td>
					<td>{{ help.toggle_separate_combined }}</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>{{ help.sort_process_name }}</td>
					<td>{{ help.show_hide_gpu }}</td>
					<td>{{ help.toggle_live_cumulative }}</td>
					<td>{{ help.misc_reset_processes_summary_min_max }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_cpu_times }}</td>
					<td>{{ help.show_hide_ip }}</td>
					<td>{{ help.toggle_linux_percentage }}</td>
					<td>{{ help.misc_quit }}</td>
				</tr>
				<tr>
					<td>{{ help.sort_user }}</td>
					<td>{{ help.show_hide_tcp_connection }}</td>
					<td>{{ help.toggle_cpu_individual_combined }}</td>
					<td>{{ help.misc_reset_history }}</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_alert }}</td>
					<td>{{ help.toggle_gpu_individual_combined }}</td>
					<td>{{ help.misc_delete_warning_alerts }}</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_network }}</td>
					<td>{{ help.toggle_short_full }}</td>
					<td>{{ help.misc_delete_warning_and_critical_alerts }}</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_irq }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_raid_plugin }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_sensors }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_wifi_module }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_processes }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_left_sidebar }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_quick_look }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_cpu_mem_swap }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
				<tr>
					<td>&nbsp;</td>
					<td>{{ help.show_hide_all }}</td>
					<td>&nbsp;</td>
					<td>&nbsp;</td>
				</tr>
			</tbody>
		</table>
		<h2 style="margin-top:20px">Styles</h2>
		<table class="help-styles">
			<thead>
				<tr>
					<th>Level</th>
					<th>Text</th>
					<th>Log</th>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td>DEFAULT</td>
					<td><span style="color:var(--fg)">default text</span></td>
					<td></td>
				</tr>
				<tr>
					<td>OK</td>
					<td><span class="ok">ok text</span></td>
					<td><span class="ok_log">ok_log text</span></td>
				</tr>
				<tr>
					<td>CAREFUL</td>
					<td><span class="careful">careful text</span></td>
					<td><span class="careful_log">careful_log text</span></td>
				</tr>
				<tr>
					<td>WARNING</td>
					<td><span class="warning">warning text</span></td>
					<td><span class="warning_log">warning_log text</span></td>
				</tr>
				<tr>
					<td>CRITICAL</td>
					<td><span class="critical">critical text</span></td>
					<td><span class="critical_log">critical_log text</span></td>
				</tr>
			</tbody>
		</table>

		<p style="margin-top:12px">
			For an exhaustive list of key bindings,
			<a href="https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands" style="color:var(--cyan)">click here</a>.
		</p>
		<p style="margin-top:6px">
			<a href="/docs" style="color:var(--cyan)">API documentation</a> /
			<a href="/openapi.json" style="color:var(--cyan)">OpenAPI file</a>
		</p>
		<p style="margin-top:12px;color:var(--fg2)">Press <strong style="color:var(--cyan)">h</strong> to go back to Glances.</p>
	</div>
</template>

<script>
export default {
	data() {
		return {
			help: undefined,
		};
	},
	mounted() {
		fetch("api/4/help", { method: "GET" })
			.then((response) => response.json())
			.then((response) => (this.help = response));
	},
};
</script>
