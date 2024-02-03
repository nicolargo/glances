<template>
    <div v-if="help">
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-12 col-lg-24">{{ help.version }} {{ help.psutil_version }}</div>
            </div>
            <div class="row">&nbsp;</div>
            <div class="row">
                <div class="col-sm-12 col-lg-24">
                    {{ help.configuration_file }}
                </div>
            </div>
            <div class="row">&nbsp;</div>
        </div>
        <div class="divTable" style="width: 100%">
            <div class="divTableBody">
                <div class="divTableRow">
                    <div class="divTableHead">
                        {{ help.header_sort.replace(':', '') }}
                    </div>
                    <div class="divTableHead">
                        {{ help.header_show_hide.replace(':', '') }}
                    </div>
                    <div class="divTableHead">
                        {{ help.header_toggle.replace(':', '') }}
                    </div>
                    <div class="divTableHead">
                        {{ help.header_miscellaneous.replace(':', '') }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_auto }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_application_monitoring }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_bits_bytes }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_erase_process_filter }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_cpu }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_diskio }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_count_rate }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_generate_history_graphs }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_io_rate }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_containers }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_used_free }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_help }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_mem }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_top_extended_stats }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_bar_sparkline }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_accumulate_processes_by_program }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_process_name }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_filesystem }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_separate_combined }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_kill_process }} - N/A in WebUI
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_cpu_times }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_gpu }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_live_cumulative }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_reset_processes_summary_min_max }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">
                        {{ help.sort_user }}
                    </div>
                    <div class="divTableCell">
                        {{ help.show_hide_ip }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_linux_percentage }}
                    </div>
                    <div class="divTableCell">{{ help.misc_quit }}</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_tcp_connection }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_cpu_individual_combined }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_reset_history }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_alert }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_gpu_individual_combined }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_delete_warning_alerts }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_network }}
                    </div>
                    <div class="divTableCell">
                        {{ help.toggle_short_full }}
                    </div>
                    <div class="divTableCell">
                        {{ help.misc_delete_warning_and_critical_alerts }}
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.sort_cpu_times }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.misc_edit_process_filter_pattern }} - N/A in WebUI
                    </div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_irq }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_raid_plugin }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_sensors }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_wifi_module }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_processes }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_left_sidebar }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_quick_look }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_cpu_mem_swap }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
                <div class="divTableRow">
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">
                        {{ help.show_hide_all }}
                    </div>
                    <div class="divTableCell">&nbsp;</div>
                    <div class="divTableCell">&nbsp;</div>
                </div>
            </div>
        </div>
        <div>
            <p>
                For an exhaustive list of key bindings,
                <a href="https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands"
                    >click here</a
                >.
            </p>
        </div>
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