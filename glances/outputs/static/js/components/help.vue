<template>
    <div v-if="help">
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-12 col-lg-24 title">{{ help.version }} {{ help.psutil_version }}</div>
            </div>
            <div class="row">&nbsp;</div>
            <div class="row">
                <div class="col-sm-12 col-lg-24">
                    {{ help.configuration_file }}
                </div>
            </div>
            <div class="row">&nbsp;</div>
        </div>
        <table class="table table-sm table-borderless table-striped table-hover">
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
                    <td>{{ help.sort_mem }}</td>
                    <td>{{ help.show_hide_top_extended_stats }}</td>
                    <td>{{ help.toggle_bar_sparkline }}</td>
                    <td>{{ help.misc_accumulate_processes_by_program }}</td>
                </tr>
                <tr>
                    <td>{{ help.sort_process_name }}</td>
                    <td>{{ help.show_hide_filesystem }}</td>
                    <td>{{ help.toggle_separate_combined }}</td>
                    <td>&nbsp;</td>
                </tr>
                <tr>
                    <td>{{ help.sort_cpu_times }}</td>
                    <td>{{ help.show_hide_gpu }}</td>
                    <td>{{ help.toggle_live_cumulative }}</td>
                    <td>{{ help.misc_reset_processes_summary_min_max }}</td>
                </tr>
                <tr>
                    <td>{{ help.sort_user }}</td>
                    <td>{{ help.show_hide_ip }}</td>
                    <td>{{ help.toggle_linux_percentage }}</td>
                    <td>{{ help.misc_quit }}</td>
                </tr>
                <tr>
                    <td>&nbsp;</td>
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
                    <td>{{ help.sort_cpu_times }}</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
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
        <div class="row">&nbsp;</div>
        <div>
            <p>
                For an exhaustive list of key bindings,
                <a href="https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands">click here</a>.
            </p>
        </div>
        <div>
            <p><a href="/docs">API documentation</a> / <a href="/openapi.json">OpenAPI file</a></p>
        </div>
        <div class="row">&nbsp;</div>
        <div>
            <p>Press <b>h</b> to came back to Glances.</p>
        </div>
    </div>
</template>

<script>
export default {
    data() {
        return {
            help: undefined
        };
    },
    mounted() {
        fetch('api/4/help', { method: 'GET' })
            .then((response) => response.json())
            .then((response) => (this.help = response));
    }
};
</script>