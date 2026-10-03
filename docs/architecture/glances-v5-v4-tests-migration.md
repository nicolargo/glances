# Glances v5 — migration des tests v4 (inventaire)

**Date :** 2026-10-03 · **Branche :** `develop-v5` · **Exigence :** architecture §9
(« Existing v4 unit tests must pass … not silently dropped »).

Chaque test v4 reçoit un verdict, et un seul :

| Verdict | Sens | Ce qu'on en fait |
|---|---|---|
| SHARED | Le test ne touche qu'un module que la v5 importe et exécute tel quel (`glances.processes`, `glances.secure`, `web_list`, pilotes de cartes, moteurs de conteneurs/VM…). | Il reste. S'il importe aussi du v4 au niveau du module, il doit être déplacé dans un fichier sans v4 au moment de la fusion. |
| COVERED | Un test v5 existant affirme déjà le même comportement (cité). | Supprimé avec le code v4, à la fusion. |
| PORT | Le comportement existe en v5, aucun test v5 ne l'affirme. | Porté dans un `tests/test_*_v5.py`. |
| OBSOLETE | Mécanique v4 remplacée par conception, ou fonction retirée par décision (citée). | Supprimé avec le code v4. |
| GAP | Le comportement n'existe pas en v5 et aucune décision ne le retire. | Décision du mainteneur : corriger en v5, ou retirer par décision écrite. |

Les fichiers de tests v4 restent en place jusqu'à la fusion `develop-v5 → develop` :
ils testent du code v4 encore présent sur cette branche, et la fusion hebdomadaire
`develop → develop-v5` les met encore à jour.

## Synthèse

| Groupe | Tests | SHARED | COVERED | PORT | OBSOLETE | GAP |
|---|---:|---:|---:|---:|---:|---:|
| 1 — plugins de base (mem, cpu, load, network, diskio, fs…) | 318 | 0 | 182 | 23 | 105 | 8 |
| 2 — autres plugins (sensors, gpu, conteneurs, VM, ports…) | 261 | 117 | 89 | 23 | 24 | 8 |
| 3 — moteur et modules partagés (core, processus, actions, AMP) | 219 | 83 | 52 | 9 | 63 | 12 |
| 4 — serveur, API, TUI, WebUI, stdout | 179 | 0 | 92 | 33 | 40 | 14 |
| 5 — exporteurs (dont 9 scripts `.sh`) | 41 | 2 | 18 | 20 | 1 | 0 |
| **Total** | **1018** | **202** | **433** | **108** | **233** | **42** |

Les fonctions paramétrées comptent pour une. Le détail par test suit, groupe par groupe.


## v4 → v5 test migration audit, group 1 (core metrics, network/disk/fs, hide_zero, views)

Branch `develop-v5`. Read-only audit. All 365 v4 test items in this group (318 test functions, counted
before parametrization) pass today:
`PYTHONPATH=. uv run pytest tests/test_plugin_{mem,memswap,load,cpu,percpu,quicklook,network,diskio,fs}.py tests/test_cpu_percent.py tests/test_plugin_init_value.py tests/test_plugin_model.py tests/test_rate_on_list.py tests/test_hide_zero_*.py tests/test_network_hide_threshold.py tests/test_lazy_views.py` gives 365 passed.

**SHARED = 0 for the whole group.** Every file imports only v4-only modules: `glances.plugins.<name>` v4 plugins,
`glances.plugins.plugin.model`, `glances.cpu_percent`, `glances.config`, `glances.thresholds`. v5 imports none of them.
`glances.cpu_percent` and `glances.plugins.load` helpers are used only by v4 plugins. Their v5 replacement is
`glances/cpu_sampler_v5.py`.

Abbreviations: `B` = `tests/test_plugin_base_v5.py`. "views → `_levels`" means that v5 replaced the v4 `views`/`decoration`
dict with the `_levels` payload entry (architecture §3.3). "No reset()" means that v5's base has no `reset()`/`get_init_value()`:
a failed cycle skips the store write (`B::test_grab_exception_does_not_crash_and_skips_store`).
"export ≠ raw by design" means that `get_export()` strips `_*` and `exportable: False` (decisions doc l.1025).
`msg_curse` was replaced by the per-plugin `render_curses_v5.render()`.

---

### tests/test_plugin_mem.py (51)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_mem_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | COVERED | `tests/test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` (mem in subset) |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` (mem keeps the default) |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (`mem: [percent]`) |
| test_update_returns_dict | COVERED | `tests/test_plugin_mem_v5.py::test_update_writes_psutil_fields_to_store` |
| test_update_contains_mandatory_keys | PORT | v5 asserts only total/available/percent. Extend `test_update_writes_psutil_fields_to_store` to assert `used`, `free` also reach the payload (`glances/plugins/mem/model_v5.py`). |
| test_memory_values_positive | GAP | v4 forces `used = max(0, total - available)` (`glances/plugins/mem/__init__.py:213-216`, LXC/cgroup-v2 over-commit). v5 forwards psutil's raw `used` (`model_v5.py::_grab_stats`). No clamp and no decision. |
| test_memory_percent_in_valid_range | GAP | v4 clamps `percent` to [0,100] (`mem/__init__.py:217-218`). v5 has no clamp, so `available > total` in a container yields a negative percent. |
| test_used_plus_free_less_than_total | GAP | Same root cause: v4 redefines `used` as `total - available`, while v5 publishes psutil's platform `used` (Linux: total-free-buffers-cached). This changes `/api` values. |
| test_total_memory_reasonable | COVERED | psutil pass-through (`test_update_writes_psutil_fields_to_store`). Real-host cycle in `tests/test_history_v5.py::test_a_real_cycle_publishes_numbers_for_every_historised_field[mem]` |
| test_active_inactive_memory | PORT | Fixture `_make_vm` carries active/inactive but no v5 assertion. Fold into the payload-completeness assertion above (`mem/model_v5.py`). |
| test_buffers_cached_memory | PORT | Same as above for buffers/cached. |
| test_update_views_creates_views | OBSOLETE | views → `_levels`. `tests/test_plugin_mem_v5.py::test_default_thresholds_drive_percent_level` |
| test_views_contain_percent_decoration | OBSOLETE | Same: the percent level is asserted by `test_default_thresholds_drive_percent_level` |
| test_get_stats_returns_json | OBSOLETE | v4 `get_stats()` JSON string. REST JSON: `tests/test_routes_v5.py::test_plugin_payload_scalar` |
| test_json_contains_expected_fields | COVERED | `tests/test_plugin_mem_v5.py::test_update_writes_psutil_fields_to_store` + `tests/test_routes_v5.py::test_plugin_payload_scalar` |
| test_history_enable_check | OBSOLETE | v4 method. History on/off: `tests/test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_get_items_history_list | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_reset_clears_stats | OBSOLETE | No reset() (see header) |
| test_reset_views | OBSOLETE | views → `_levels` |
| test_fields_description_exists | COVERED | `tests/test_plugin_mem_v5.py::test_plugin_declares_percent_as_watched`. `/info`: `tests/test_routes_v5.py::test_plugin_info_returns_schema` |
| test_mandatory_fields_described | PORT | Covered once the payload-completeness assertion lands, because undeclared fields are stripped (`test_update_drops_undeclared_fields`). |
| test_field_has_description | PORT | No v5 test checks schema completeness. Add one generic test parametrized over `glances.main_v5.discover_plugin_classes()`: each `fields_description` entry has `description` and `unit`. |
| test_field_has_unit | PORT | Same generic test. |
| test_get_alert_log_returns_valid_status | OBSOLETE | v4 `get_alert_log`/`_LOG` strings. Ladder: `tests/test_plugin_mem_v5.py::test_default_thresholds_drive_percent_level` |
| test_msg_curse_returns_list | OBSOLETE | msg_curse → render. `tests/test_plugin_mem_render_curses_v5.py::test_render_produces_four_rows` |
| test_msg_curse_format | OBSOLETE | Same |
| test_msg_curse_structure | COVERED | `tests/test_plugin_mem_render_curses_v5.py::test_render_produces_four_rows`, `::test_render_first_row_carries_mem_title` |
| test_zfs_enabled_attribute | GAP | v4 adds the ZFS ARC to `cached`/`available` and subtracts the shrinkable part from `used` (`mem/__init__.py:179-210`, issue #3979). v5 `mem/model_v5.py` has no ZFS code. The only mention is a G2 scope cut for *quicklook* (`tui-v4-rendering-patterns.md:554,585`), not a decision in the decisions doc. |
| test_available_config_option | GAP | `[mem] available` is `❌ absent` in `glances-v5-v4-parity-inventory.md` §11. v5 TUI shows `available` unconditionally (`mem/render_curses_v5.py:114`). Not decided. |
| test_get_export_returns_dict | COVERED | `tests/test_plugin_mem_v5.py::test_get_export_strips_internals` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design. `test_get_export_strips_internals` |
| test_export_contains_stats_when_available | COVERED | `tests/test_plugin_mem_v5.py::test_get_export_strips_internals` |
| TestMemPluginMMM (18 tests): test_percent_field_has_mmm_flag, test_mmm_fields_initialized, test_mmm_field_structure, test_percent_min_max_mean_generated_descriptions, test_percent_min_max_mean_in_stats_after_update, test_percent_min_max_mean_are_numeric, test_percent_min_max_mean_in_valid_range, test_min_less_than_or_equal_max, test_mean_between_min_and_max, test_current_percent_within_bounds, test_mmm_fields_in_api_output, test_mmm_fields_in_json_output, test_mmm_fields_in_export_output, test_mmm_history_accumulation, test_mmm_min_max_monotonic, test_mmm_history_limit, test_mmm_fields_with_multiple_updates, test_mmm_decorator_applied | OBSOLETE (×18) | "Dropped — min/max/mean `mmm` (maintainer decision, 2026-09-26)", decisions doc §10 l.1711 |

### tests/test_plugin_memswap.py (30)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_memswap_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | PORT | `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` only pins cpu/mem/load/network/percpu. Add memswap (and diskio, fs) to the enabled-by-default subset (`glances/main_v5.py::discover_plugins`). |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_update_returns_dict | COVERED | `tests/test_plugin_memswap_v5.py::test_update_writes_swap_fields` |
| test_update_contains_mandatory_keys | COVERED | `test_update_writes_swap_fields` (total/used/free/percent) |
| test_swap_values_non_negative | COVERED | `test_update_writes_swap_fields` (used>0, free>0; pass-through) |
| test_swap_percent_in_valid_range | COVERED | pass-through (`test_update_writes_swap_fields`). v4 memswap has no clamp either |
| test_sin_sout_present | COVERED | `test_first_cycle_rate_fields_are_none`, `test_second_cycle_computes_swap_rates` |
| test_time_since_update_present | COVERED | `B::test_time_since_update_zero_on_first_cycle` |
| test_update_views_creates_views | OBSOLETE | views → `_levels`. `test_percent_level_uses_default_thresholds` |
| test_views_contain_percent_decoration | OBSOLETE | Same |
| test_get_stats_returns_json | OBSOLETE | `tests/test_routes_v5.py::test_plugin_payload_scalar` |
| test_json_contains_expected_fields | COVERED | `test_update_writes_swap_fields` + `test_routes_v5.py::test_plugin_payload_scalar` |
| test_history_enable_check | OBSOLETE | `tests/test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_get_items_history_list | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_percent_is_watched_prominent` |
| test_mandatory_fields_described | COVERED | `test_total_used_free_are_bytes_not_watched`, `test_percent_is_watched_prominent` |
| test_sin_sout_fields_described | COVERED | `test_sin_sout_are_rate_counters` |
| test_field_has_description | PORT | Generic schema-completeness test (see mem) |
| test_byte_fields_have_unit | COVERED | `test_total_used_free_are_bytes_not_watched` (sin/sout unit falls under the generic PORT) |
| test_get_alert_log_returns_valid_status | OBSOLETE | `test_percent_level_uses_default_thresholds`, `test_percent_level_ok_when_low` |
| test_msg_curse_returns_list | OBSOLETE | `tests/test_plugin_memswap_render_curses_v5.py::test_render_produces_four_rows` |
| test_msg_curse_not_empty_with_stats | COVERED | `test_plugin_memswap_render_curses_v5.py::test_render_produces_four_rows` |
| test_msg_curse_contains_title | COVERED | `test_plugin_memswap_render_curses_v5.py::test_render_first_row_carries_swap_title` |
| test_get_export_returns_stats | COVERED | `test_get_export_strips_internals_and_levels` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design |
| test_handles_no_swap_gracefully | COVERED | `test_update_handles_no_swap_configured` |

### tests/test_plugin_load.py (32)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_load_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | COVERED | `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (min1/5/15) |
| test_update_returns_dict | COVERED | `test_update_writes_loadavg_to_store` |
| test_update_contains_mandatory_keys | COVERED | `test_update_writes_loadavg_to_store` (min1/5/15 + cpucore) |
| test_load_values_non_negative | COVERED | pass-through (`test_update_writes_loadavg_to_store`) |
| test_cpucore_positive | COVERED | `test_levels_fall_back_to_one_core_when_cpucount_unknown` + `test_update_writes_loadavg_to_store` |
| test_update_views_creates_views | OBSOLETE | views → `_levels` |
| test_views_contain_min15_decoration | OBSOLETE | `test_min15_level_normalized_by_cpucore_prominent` |
| test_views_contain_min5_decoration | OBSOLETE | `test_min5_level_normalized_by_cpucore_non_prominent` |
| test_get_stats_returns_json | OBSOLETE | `test_routes_v5.py::test_plugin_payload_scalar` |
| test_json_contains_expected_fields | COVERED | `test_update_writes_loadavg_to_store`. `cpucore` is `internal` and kept by `get_api_payload` (`B::test_get_api_payload_keeps_levels` family) |
| test_history_enable_check | OBSOLETE | `test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_get_items_history_list | COVERED | `test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_min15_is_watched_prominent` |
| test_mandatory_fields_described | COVERED | `test_min1_is_not_watched`, `test_min5_is_watched_non_prominent`, `test_min15_is_watched_prominent`, cpucore via `test_update_writes_loadavg_to_store` |
| test_field_has_description | PORT | Generic schema-completeness test |
| test_msg_curse_returns_list | OBSOLETE | `tests/test_plugin_load_render_curses_v5.py::test_render_produces_four_rows` |
| test_msg_curse_format | OBSOLETE | Same |
| test_msg_curse_structure | COVERED | `test_plugin_load_render_curses_v5.py::test_render_produces_four_rows`, `::test_render_first_row_has_load_title` |
| test_log_core_returns_int | COVERED | v5 equivalent `cpu_sampler_v5.sampler.cpu_count`: `tests/test_cpu_sampler_v5.py::test_cpu_count_is_lazy_and_cached`, `::test_cpu_count_falls_back_to_one_when_psutil_returns_none` |
| test_phys_core_returns_int | COVERED | `tests/test_plugin_core_v5.py::test_update_writes_phys_and_log` |
| test_load_average_returns_tuple | COVERED | `test_plugin_load_v5.py::test_update_writes_loadavg_to_store` (v5 calls `psutil.getloadavg` directly) |
| test_load_average_values_non_negative | COVERED | Same (pass-through) + `test_update_swallows_loadavg_oserror` |
| test_load_average_percent_mode | PORT | v4 `load_average(percent=True)` feeds quicklook. v5 computes `load = round(load15 / sampler.cpu_count * 100, 1)` in `glances/plugins/quicklook/model_v5.py::_collect_sync`, but every quicklook test mocks `_collect_sync`. Patch `psutil.getloadavg` and `sampler.cpu_count`, then assert the value. |
| test_alert_based_on_cpucore | COVERED | `test_min15_level_normalized_by_cpucore_prominent`, `test_levels_ok_when_below_careful_per_core` |
| test_get_export_returns_dict | COVERED | generic `B::test_scalar_get_export_strips_internals_and_levels` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design |
| test_export_contains_load_values_when_available | COVERED | generic `B::test_scalar_get_export_strips_internals_and_levels` (load has no own export test; low value) |

### tests/test_plugin_cpu.py (28)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_cpu_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | COVERED | `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins`, `::test_shipped_defaults_resolve_as_expected` |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (user/system) |
| test_update_returns_dict | COVERED | `test_update_writes_aggregate_fields` |
| test_update_contains_mandatory_keys | COVERED | `test_update_writes_aggregate_fields` (total/system/user/idle) |
| test_cpu_percentages_in_valid_range | COVERED | `tests/test_cpu_sampler_v5.py::test_aggregate_percentages_are_computed_from_cpu_times_deltas`, `::test_decreasing_counter_is_clamped_to_zero`, `::test_degenerate_window_never_reports_a_busy_cpu` |
| test_total_cpu_calculation | COVERED | `test_update_writes_aggregate_fields` (total = 100 - idle) |
| test_cpucore_count | COVERED | `test_update_writes_aggregate_fields` (cpucore == 4) |
| test_ctx_switches_present | COVERED | `test_second_cycle_computes_ctx_switches_rate` |
| test_interrupts_present | COVERED | `test_interrupts_and_soft_interrupts_and_syscalls_are_rate_only`, `test_first_cycle_rate_fields_are_none` |
| test_soft_interrupts_present | COVERED | Same |
| test_update_views_creates_views | OBSOLETE | views → `_levels` |
| test_views_contain_decoration | OBSOLETE | `test_total_level_uses_default_thresholds` |
| test_get_stats_returns_json | OBSOLETE | `test_routes_v5.py::test_plugin_payload_scalar` |
| test_json_contains_expected_fields | COVERED | `test_update_writes_aggregate_fields` + `test_routes_v5.py::test_plugin_payload_scalar` |
| test_history_enable_check | OBSOLETE | `test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_get_items_history_list | COVERED | `test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_total_is_watched_prominent` |
| test_mandatory_fields_described | COVERED | `test_update_writes_aggregate_fields` (undeclared fields stripped, `test_update_drops_undeclared_psutil_fields`) |
| test_field_has_description | PORT | Generic schema-completeness test |
| test_get_alert_returns_valid_status | OBSOLETE | v4 `get_alert` strings. `test_total_level_uses_default_thresholds` |
| test_alert_levels | COVERED | `test_total_level_uses_default_thresholds`, `test_user_config_overrides_total_threshold` |
| test_msg_curse_returns_list | OBSOLETE | `tests/test_plugin_cpu_render_curses_v5.py::test_render_produces_four_rows` |
| test_msg_curse_format | OBSOLETE | Same |
| test_msg_curse_has_title_when_enabled | COVERED | `test_plugin_cpu_render_curses_v5.py::test_render_first_row_has_cpu_title` |

### tests/test_plugin_percpu.py (6)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_summary_is_the_leftover_mean_not_the_displayed_mean | COVERED | `tests/test_plugin_percpu_render_curses_v5.py::test_render_overflow_row_averages_the_hidden_cores` |
| test_summary_ignores_the_displayed_cores_entirely | COVERED | Same (CPU* = mean of hidden 10, 0 only) |
| test_summary_averages_rather_than_sums | COVERED | Same (5.0, not 10.0) |
| test_summary_covers_every_core_that_is_not_displayed | COVERED | Same + `::test_the_core_cap_comes_from_the_payload` |
| test_one_percentage_per_header_column | COVERED | `::test_render_overflow_row_averages_the_hidden_cores` (total and user columns) |
| test_no_summary_row_when_every_core_fits | COVERED | `::test_render_no_overflow_row_when_exact_max` |

### tests/test_plugin_quicklook.py (17)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_a_plain_list_is_honoured | COVERED | `tests/test_plugin_quicklook_v5.py::TestStatsList::test_a_plain_list_is_honoured` |
| test_whitespace_around_items_is_ignored | COVERED | `TestStatsList::test_whitespace_around_items_is_ignored` + `tests/test_config_v5.py::test_get_list_strips_whitespace_and_empty` |
| test_a_typo_falls_back_to_the_default_not_to_everything | COVERED | `TestStatsList::test_a_typo_falls_back_to_the_default_not_to_everything`, `::test_gpu_is_opt_in` |
| test_the_gpu_entries_are_still_selectable_on_purpose | COVERED | `TestStatsList::test_gpu_is_opt_in` |
| test_no_list_configured_uses_the_default | COVERED | `TestStatsList::test_default_is_cpu_mem_load` |
| test_a_busy_core_is_not_hidden_by_a_quiet_average | COVERED | `TestPercpuLevels::test_a_pegged_core_is_critical_while_an_idle_one_is_ok` |
| test_each_threshold_boundary | COVERED | The per-core pass calls `compute_level`: `tests/test_thresholds_v5.py::test_compute_level_high_direction` (49.99/50/70/90) + `TestPercpuLevels::test_a_quicklook_critical_override_changes_the_per_core_levels` |
| test_the_summary_row_is_styled_by_the_cores_it_averages | PORT | `TestPercpuLevels::test_percpu_other_is_the_mean_and_level_of_the_hidden_cores` yields `ok`, the same as the aggregate, so it cannot catch the row borrowing a wrong level. Add cores `[95,95,95,95,60,60]` and expect `percpu_other == {"total": 60.0, "level": "careful"}` (`quicklook/model_v5.py::_decorate_percpu`). |
| test_no_summary_row_when_every_core_is_shown | COVERED | `TestPercpuLevels::test_percpu_other_is_none_at_or_under_max_cpu_display` |
| test_the_styles_reach_the_curses_bars | COVERED | `tests/test_plugin_quicklook_render_curses_v5.py::TestPercpuOwnLevel::test_a_hot_core_is_critical_while_the_aggregate_cpu_is_ok` |
| test_scanning_the_cores_does_not_move_the_global_threshold | OBSOLETE | The v4 `glances_thresholds` singleton keyed `quicklook_cpu` does not exist in v5. Per-core levels stay out of `_levels`, and quicklook has `EMITS_ALERTS=False` (`test_plugin_quicklook_v5.py::test_quicklook_opts_out_of_alerts`). |
| test_limits_carry_stripped_items | COVERED | v5 has no `get_limits('list')`. `test_config_v5.py::test_get_list_strips_whitespace_and_empty` + `TestStatsList::test_whitespace_around_items_is_ignored` |
| test_a_hide_pattern_written_with_spaces_still_hides | PORT | Holds only by composition: `_compile_filter` → `config.get(...,[])` → list coercion. Add `hide=lo, docker.*` (with a space) to `B::test_collection_hide_drops_matching_items` (`glances/plugins/plugin/base_v5.py::_compile_filter`). |
| test_internal_spaces_are_kept | PORT | `B::test_collection_alias_published_when_pk_matches` covers an internal space but not a space around the comma. Assert `alias=sda1:System Disk , sdb1:Data Disk` gives exactly `System Disk` / `Data Disk` (`base_v5.py::_read_alias`). |
| test_the_gpu_entries_are_historised | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (quicklook gpu_mem/gpu_proc) + `::test_only_history_fields_are_recorded` |
| test_a_gpu_entry_is_drawn_as_a_sparkline_of_its_history | OBSOLETE | `--sparkline` / `S` was set aside by the maintainer (2026-09-25, decisions §10 CLI row and the Phase 2.X `S` line). Revisit if the sparkline is ported. |
| test_a_gpu_entry_is_historised_even_when_not_in_the_list | COVERED | In v5 the list is display-only and collection is unconditional (`quicklook/model_v5.py` comment). `test_plugin_quicklook_v5.py::test_gpu_means_from_store` (default list) + history declaration test |

### tests/test_plugin_network.py (39)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_network_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | COVERED | `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_get_key_returns_interface_name | COVERED | `test_plugin_identity` (`_primary_key == "interface_name"`) |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (bytes_recv/bytes_sent; `*_rate_per_sec` names dropped, decided 2026-09-26 in the `--fetch` row) |
| test_update_returns_list | COVERED | `test_grab_stats_returns_one_dict_per_interface` |
| test_each_interface_has_name | COVERED | Same |
| test_bytes_recv_and_sent_present | COVERED | `test_second_cycle_computes_per_interface_rates` |
| test_bytes_values_non_negative | COVERED | `B::test_rate_field_clamps_negative_delta_to_zero` |
| test_rate_fields_after_two_updates | COVERED | `test_second_cycle_computes_per_interface_rates` |
| test_bytes_all_calculated | COVERED | No `bytes_all` field by design (decisions §10, `T` line: renderers sum the two rates). `tests/test_plugin_network_render_curses_v5.py::test_combined_mode_replaces_the_two_columns_with_their_sum`, `::test_cumulative_and_combined_compose_without_the_per_second_suffix` |
| test_is_up_field_present | COVERED | `test_is_up_flows_through` |
| test_speed_field_present | COVERED | `speed` became `bytes_speed_rate_per_sec`: `test_bytes_speed_rate_per_sec_computed_from_speed`, `::test_bytes_speed_rate_per_sec_is_zero_for_unknown_speed` |
| test_alias_field_present | COVERED | `test_alias_published_for_matching_interface` + `B::test_collection_alias_absent_by_default` (v5 omits the key when unconfigured, by design) |
| test_update_views_creates_views | OBSOLETE | views → `_levels` |
| test_views_keyed_by_interface | OBSOLETE | `test_levels_indexed_by_interface_name` |
| test_get_stats_returns_json | OBSOLETE | `test_routes_v5.py::test_plugin_payload_collection` |
| test_json_preserves_interface_data | COVERED | `test_routes_v5.py::test_plugin_payload_collection` + `test_grab_stats_returns_one_dict_per_interface` |
| test_history_enable | OBSOLETE | `test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_schema_watched_fields` |
| test_mandatory_fields_described | COVERED | `test_plugin_identity`, `test_schema_watched_fields` |
| test_rate_fields_described | COVERED | `test_schema_watched_fields` (rate True on bytes_recv/bytes_sent) |
| test_hide_zero_attribute | COVERED | `B::test_hide_zero_config_defaults` |
| test_hide_zero_fields_defined | COVERED | `test_plugin_network_v5.py::test_hide_zero_fields_declared` |
| test_hide_no_up_attribute | COVERED | `test_hide_no_up_off_by_default_keeps_down_interfaces`, `::test_hide_no_up_drops_down_interfaces_when_enabled` |
| test_hide_no_ip_attribute | COVERED | `test_hide_no_ip_drops_link_only_interfaces_when_enabled` (+ 2 siblings) |
| test_msg_curse_empty_without_max_width | OBSOLETE | v4 msg_curse internals |
| test_msg_curse_with_args_and_max_width | OBSOLETE | Render covered by `tests/test_plugin_network_render_curses_v5.py` (e.g. `test_render_one_row_per_interface_plus_header`) |
| test_sorted_stats_returns_list | OBSOLETE | v4 method type check |
| test_sorted_stats_preserves_count | GAP | The behaviour behind `sorted_stats()` is missing. v4 `msg_curse` draws interfaces natural-sorted by alias-or-name (`plugin/model.py:444-464`, `network/__init__.py:323`). v5 `network/render_curses_v5.py:165` iterates payload (psutil) order with no sort. No decision. |
| test_get_export_returns_list | COVERED | `test_get_export_strips_internals_and_returns_list` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design |
| test_views_have_decoration | OBSOLETE | `test_levels_indexed_by_interface_name` |
| test_saturated_tx_is_flagged_while_rx_is_idle | PORT | Only the rx direction is tested. Add rx=0, tx at about 0.95×capacity on a 1 Gbit link and expect `_levels["eth0"]["bytes_sent"]` critical and `bytes_recv` ok. Ideally parametrize (rx,tx) over (0,sat),(sat,0),(0,0),(sat,sat) (`network/model_v5.py`). |
| test_saturated_rx_is_flagged_while_tx_is_idle | COVERED | `test_levels_indexed_by_interface_name` (rx warning with tx=0) |
| test_a_fully_idle_interface_is_ok_not_undecorated | PORT | No v5 test asserts an `ok` entry at rate 0 on a known-speed link. Same parametrized test as above. |
| test_both_directions_busy_still_alert | COVERED | `test_levels_indexed_by_interface_name` + schema symmetry `test_schema_bandwidth_fields_normalize_by_speed` (fold into the parametrized PORT anyway) |

### tests/test_plugin_diskio.py (41)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_diskio_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | PORT | Add diskio to `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` subset |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_get_key_returns_disk_name | COVERED | `test_disk_name_is_primary_key` |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` (read_bytes/write_bytes) |
| test_update_returns_list | COVERED | `test_update_yields_one_entry_per_disk` |
| test_each_disk_has_name | COVERED | Same |
| test_read_write_bytes_present | COVERED | `test_second_cycle_computes_byte_rates` |
| test_bytes_values_non_negative | COVERED | `B::test_rate_field_clamps_negative_delta_to_zero` |
| test_rate_fields_after_two_updates | COVERED | `test_second_cycle_computes_byte_rates` |
| test_latency_fields_present | COVERED | `test_latency_is_time_rate_over_count_rate` |
| test_latency_values_non_negative | COVERED | `test_latency_is_zero_without_operations`, `test_latency_is_none_on_the_first_cycle` |
| test_read_count_present | COVERED | `test_read_write_count_are_rate_internal` + `tests/test_plugin_diskio_render_curses_v5.py::test_iops_mode_swaps_both_the_columns_and_the_header` |
| test_write_count_present | COVERED | Same |
| test_update_views_creates_views | OBSOLETE | views → `_levels` |
| test_views_keyed_by_disk | OBSOLETE | `test_read_bytes_threshold_from_config_triggers_level` (`_levels["sda"]`) |
| test_get_stats_returns_json | OBSOLETE | `test_routes_v5.py::test_plugin_payload_collection` |
| test_json_preserves_disk_data | COVERED | `test_routes_v5.py::test_plugin_payload_collection` + `test_update_yields_one_entry_per_disk` |
| test_history_enable | OBSOLETE | `test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_read_write_bytes_are_rate_counters` |
| test_mandatory_fields_described | COVERED | `test_disk_name_is_primary_key`, `test_read_write_bytes_are_rate_counters` |
| test_rate_fields_described | COVERED | `test_read_write_bytes_are_rate_counters`, `test_read_write_count_are_rate_internal` |
| test_latency_fields_described | COVERED | `test_latency_fields_are_internal_opt_in_alerts_under_v4_keys` |
| test_hide_zero_attribute | COVERED | `B::test_hide_zero_config_defaults` |
| test_hide_zero_fields_defined | COVERED | `test_plugin_diskio_v5.py::test_hide_zero_fields_declared` |
| test_hide_threshold_bytes_attribute | COVERED | `B::test_hide_zero_config_reads_from_section`, `test_plugin_diskio_v5.py::test_hide_zero_sticky_after_threshold_burst` |
| test_msg_curse_returns_list | OBSOLETE | Render: `tests/test_plugin_diskio_render_curses_v5.py` |
| test_msg_curse_empty_without_max_width | OBSOLETE | v4 internals |
| test_msg_curse_with_max_width | OBSOLETE | `test_plugin_diskio_render_curses_v5.py::test_render_block_width_fits_sidebar_cap` |
| test_sorted_stats_returns_list | OBSOLETE | v4 method type check |
| test_sorted_stats_preserves_count | GAP | v4 natural-sorts by alias-or-name (`sorted_stats`, `diskio/__init__.py:257`). v5 sorts by raw `disk_name` with plain string order (`diskio/render_curses_v5.py:169`, `test_render_disks_sorted_by_name`): `sda10` sorts before `sda2`, and an alias does not move a row. No decision. |
| test_get_export_returns_list | COVERED | generic `B::test_collection_get_export_returns_list` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design |
| test_views_have_decoration | OBSOLETE | `test_read_bytes_threshold_from_config_triggers_level` |
| test_alias_field_may_be_present | COVERED | `test_alias_published_for_matching_disk` |
| test_alert_follows_the_rate_not_the_lifetime_counter | PORT | In v5 the rate replaces the counter in place, but every diskio/base rate-level test starts the counter at 0, so counter == rate and a level computed on the counter would pass too. Add: cycle-1 counter 5e9, cycle-2 +10 B over 1 s, `[diskio] sda_read_bytes_critical=90` (v5 key; v4 `sda_rx_*` renamed, decided) → level `ok` (`diskio/model_v5.py` / `base_v5._derived_parameters`). |
| test_a_busy_disk_still_raises_the_alert | COVERED | `test_read_bytes_threshold_from_config_triggers_level` |
| test_the_rate_field_the_webui_reads_is_decorated_too | OBSOLETE | No separate `*_rate_per_sec` field in v5. TUI and WebUI read the same `_levels`, which REST keeps (`B::test_get_api_payload_keeps_levels`) |
| test_a_missing_rate_on_the_first_sample_does_not_raise | COVERED | `test_first_cycle_rate_fields_are_none` + `tests/test_thresholds_v5.py::test_compute_level_none_value_returns_ok` |

### tests/test_plugin_fs.py (40)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_plugin_name | COVERED | `tests/test_plugin_fs_v5.py::test_plugin_identity` |
| test_plugin_is_enabled | PORT | Add fs to `test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` subset |
| test_display_curse_enabled | COVERED | `B::test_display_in_tui_defaults_true` |
| test_get_key_returns_mnt_point | COVERED | `test_mnt_point_is_primary_key` |
| test_history_items_defined | COVERED | `tests/test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list` |
| test_update_returns_list | COVERED | `test_update_yields_one_entry_per_partition` |
| test_each_fs_has_mnt_point | COVERED | Same |
| test_each_fs_has_device_name | COVERED | `test_update_carries_size_used_free_percent` |
| test_size_used_free_present | COVERED | Same |
| test_percent_present | COVERED | Same |
| test_size_values_positive | COVERED | pass-through of `psutil.disk_usage` (same test) |
| test_used_values_non_negative | COVERED | Same |
| test_free_values_non_negative | COVERED | Same |
| test_percent_in_valid_range | COVERED | Same |
| test_used_plus_free_equals_size | COVERED | Same (psutil values forwarded unchanged) |
| test_fs_type_present | COVERED | `test_update_carries_size_used_free_percent` (fs_type) |
| test_options_present | COVERED | `test_fs_type_and_options_are_internal` |
| test_update_views_creates_views | OBSOLETE | views → `_levels` |
| test_views_keyed_by_mnt_point | OBSOLETE | `test_levels_indexed_by_mnt_point` |
| test_views_have_used_decoration | OBSOLETE | `test_levels_indexed_by_mnt_point` + `tests/test_plugin_fs_render_curses_v5.py::test_render_used_cell_inherits_percent_level` |
| test_get_stats_returns_json | OBSOLETE | `test_routes_v5.py::test_plugin_payload_collection` |
| test_json_preserves_fs_data | COVERED | `test_routes_v5.py::test_plugin_payload_collection` + `test_update_carries_size_used_free_percent` |
| test_history_enable | OBSOLETE | `test_history_v5.py::test_history_size_zero_or_the_flag_disables` |
| test_reset_clears_stats | OBSOLETE | No reset() |
| test_reset_views | OBSOLETE | views |
| test_fields_description_exists | COVERED | `test_percent_is_watched_but_not_prominent` |
| test_mandatory_fields_described | COVERED | `test_mnt_point_is_primary_key`, `test_size_used_free_are_bytes_not_watched`, `test_percent_is_watched_but_not_prominent` |
| test_byte_fields_have_unit | COVERED | `test_size_used_free_are_bytes_not_watched` |
| test_msg_curse_returns_list | OBSOLETE | Render: `tests/test_plugin_fs_render_curses_v5.py` |
| test_msg_curse_empty_without_max_width | OBSOLETE | v4 internals |
| test_msg_curse_with_max_width | OBSOLETE | `test_plugin_fs_render_curses_v5.py::test_render_block_width_fits_sidebar_cap` |
| test_get_export_returns_list | COVERED | `test_get_export_strips_levels_but_keeps_metadata` |
| test_export_equals_raw | OBSOLETE | export ≠ raw by design |
| test_alias_field_may_be_present | COVERED | `test_alias_published_for_matching_mountpoint` |
| test_alias_matches_mixed_case_mount_point | PORT | v5 lower-cases both sides (`base_v5.py::_read_alias` l.466, `_apply_alias` l.789), but every alias test uses a lower-case key. Add `[fs] alias=/Volumes/SSD:SSD` with mount `/Volumes/SSD` and expect `alias == "SSD"` (`test_plugin_fs_v5.py`). |
| test_get_disk_partitions_returns_list | OBSOLETE | v4 helper. v5 `_collect_sync` covered by `test_update_yields_one_entry_per_partition`, `test_update_handles_permission_error_globally` (note: v4 also caught `UnicodeDecodeError`. In v5 it would end up in the base "update failed" path: no crash, but the cycle is lost) |
| test_get_disk_partitions_fetch_all | COVERED | `test_allow_adds_extra_fs_types_from_fetch_all`, `test_allow_off_by_default_does_not_call_fetch_all` |
| test_physical_partitions_subset_of_all | OBSOLETE | psutil property on a v4 helper. Dedup: `test_allow_does_not_duplicate_already_tracked_mount` |
| test_views_skip_ro_mounts_for_threshold | GAP | v4 skips threshold decoration for `ro` mounts (`fs/__init__.py:270-271`, issue #3143). v5 `fs/model_v5.py` levels every mount, so read-only volumes at 100% (squashfs/snaps, ISO) alert. Only `tui-v4-rendering-patterns.md:217-219` calls this intentional ("operators can suppress via show/hide"). The decisions doc has no drop decision, and its standing rule requires one. Needs a maintainer ruling. |
| test_can_get_conf_value | COVERED | `test_allow_adds_extra_fs_types_from_fetch_all` (`[fs] allow` read) |

### tests/test_cpu_percent.py (1)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_percpu_uses_guest_nice_value | PORT | `glances.cpu_percent` is v4-only. v5 `percpu/model_v5.py::_grab_stats` copies each named attribute, but the `_core()` stub in `test_plugin_percpu_v5.py` sets steal=guest_nice=0.0, so nothing would catch a swap. Feed a core with steal=8.0, guest_nice=10.0 and assert both in `data[0]`. |

### tests/test_plugin_init_value.py (2, each parametrized ×19)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_init_value_is_a_list | COVERED | v5 collection plugins (IS_COLLECTION, per-plugin `test_plugin_identity`) publish a `{"data": [...]}` envelope: `B::test_collection_update_writes_data_envelope`, `B::test_get_export_collection_before_update_returns_empty_list`, `B::test_get_api_payload_is_always_a_dict_for_a_collection`, `test_plugin_diskio_v5.py::test_update_handles_none_return` (`data == []`) |
| test_reset_leaves_the_stats_a_list | OBSOLETE | No reset() in v5 |

### tests/test_plugin_model.py (2)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_update_called_when_stats_equal_init_value_and_timer_not_finished | OBSOLETE | The v4 `_check_decorator`/`refresh_timer` gating was replaced by `GlancesScheduler` (`tests/test_scheduler_v5.py::test_run_forever_calls_plugin_update`, `::test_first_sleep_is_global_refresh_then_plugin_refresh`). Note: v5 has no "retry immediately while stats are still empty" path. A failed cycle waits one plugin refresh. |
| test_update_not_called_when_stats_differ_and_timer_not_finished | OBSOLETE | `tests/test_scheduler_v5.py::test_steady_state_sleep_still_equals_plugin_refresh_time` |

### tests/test_rate_on_list.py (5)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_a_new_stat_does_not_publish_its_lifetime_counter_as_a_delta | COVERED | `B::test_collection_rate_none_for_newly_appearing_item` (v5 publishes None, not 0) |
| test_a_new_stat_is_given_the_same_fields_as_every_other | COVERED | Same (`"rx" in items["wlan0"]`) |
| test_a_stat_already_present_still_measures_its_own_delta | COVERED | Same (`eth0` rate 500) |
| test_a_new_stat_measures_from_its_own_gauge_on_the_next_sample | PORT | No v5 test takes a newly-appeared item to a third cycle. Extend `B::test_collection_rate_none_for_newly_appearing_item`: wlan0 500→900 over 1 s gives 400.0 (`base_v5.py::_transform_gauge`). |
| test_network_update_views_survives_an_interface_appearing | COVERED | `test_plugin_network_v5.py::test_appearing_interface_has_none_rate_first_cycle` + `test_plugin_network_render_curses_v5.py::test_render_skips_interfaces_without_rate_yet` |

### tests/test_hide_zero_threshold.py (7)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_an_idle_interface_stays_hidden_across_refreshes | COVERED | `test_plugin_network_v5.py::test_hide_zero_reads_threshold_and_unhides_above_it` (cycle 2 at threshold stays hidden) + `B::test_hide_zero_boundary_equal_threshold_does_not_unhide` |
| test_an_idle_disk_stays_hidden_across_refreshes | COVERED | `B::test_hide_zero_boundary_equal_threshold_does_not_unhide` (generic. diskio opts in: `test_plugin_diskio_v5.py::test_hide_zero_fields_declared`) |
| test_traffic_reveals_the_field_and_it_does_not_hide_again | COVERED | `B::test_hide_zero_sticky_after_burst_then_back_to_zero`, network `test_hide_zero_reads_threshold_and_unhides_above_it` |
| test_one_byte_per_second_is_traffic | COVERED | `B::test_hide_zero_boundary_equal_threshold_does_not_unhide` (strict `>`) |
| test_a_rate_equal_to_the_threshold_is_hidden | COVERED | Same |
| test_a_rate_above_the_threshold_is_shown | COVERED | Same (1001 > 1000) + `test_plugin_diskio_v5.py::test_hide_zero_sticky_after_threshold_burst` |
| test_hide_zero_false_never_hides | COVERED | `B::test_hide_zero_off_by_default_publishes_false_and_keeps_item`, `test_plugin_network_v5.py::test_hide_zero_off_by_default_never_hides` |

### tests/test_hide_zero_row_visibility.py (5)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_the_two_fields_really_do_disagree | OBSOLETE | v5 publishes one `hidden` boolean per item, not one per field. This is a documented deliberate divergence (`glances-v5-v4-parity-inventory.md` §14 `hide_zero` row). |
| test_a_read_only_disk_is_still_displayed | COVERED | `B::test_hide_zero_row_visible_when_one_field_unhides` + `test_plugin_diskio_render_curses_v5.py::test_render_skips_hidden_disks` |
| test_a_write_only_disk_is_still_displayed | PORT | v5 tests only the first HIDE_ZERO field moving (rx / read). Parametrize `B::test_hide_zero_row_visible_when_one_field_unhides` over rx/tx (`base_v5.py::_compute_hide_zero` reduction). |
| test_a_disk_below_the_threshold_on_both_rates_is_dropped | COVERED | `B::test_hide_zero_boundary_equal_threshold_does_not_unhide` + `test_plugin_diskio_render_curses_v5.py::test_render_skips_hidden_disks` |
| test_a_busy_disk_is_displayed_beside_a_hidden_one | COVERED | `test_plugin_diskio_render_curses_v5.py::test_render_skips_hidden_disks` |

### tests/test_network_hide_threshold.py (5)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_the_option_reaches_the_plugin | COVERED | `B::test_hide_zero_config_reads_from_section`, `test_plugin_network_v5.py::test_hide_zero_reads_threshold_and_unhides_above_it` |
| test_it_defaults_to_zero_when_not_configured | COVERED | `B::test_hide_zero_config_defaults` |
| test_traffic_below_the_threshold_leaves_the_interface_hidden | COVERED | `test_plugin_network_v5.py::test_hide_zero_reads_threshold_and_unhides_above_it` |
| test_traffic_above_the_threshold_reveals_the_interface | COVERED | Same |
| test_without_a_threshold_any_traffic_reveals_the_interface | COVERED | `test_plugin_network_v5.py::test_hide_zero_row_visible_when_only_one_direction_moves` (threshold 0, rx 500) |

### tests/test_lazy_views.py (7)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_refresh_builds_nothing | OBSOLETE | v4 lazy processlist views. v5 computes `_levels` in the model (`tests/test_plugin_processlist_v5.py::test_cpu_percent_default_thresholds_trigger_level`) |
| test_first_read_builds_the_views | OBSOLETE | Same |
| test_second_read_reuses_the_built_views | OBSOLETE | Same |
| test_json_contains_every_process | OBSOLETE | v4 `get_json_views`. REST: `test_routes_v5.py::test_plugin_payload_collection` |
| test_reset_stays_reset | OBSOLETE | views/reset |
| test_set_views_is_not_overwritten | OBSOLETE | `set_views` served the v4 client/server views transfer (XML-RPC removed, decisions §1.1). The v5 client reads `_levels` from REST. |
| test_curses_rows_stop_at_the_screen_height | COVERED | `tests/test_plugin_processlist_render_curses_v5.py::test_row_budget_caps_the_number_of_processes`, `::test_the_cursor_decorates_the_row_it_names` |

---

### Summary

| v4 file | SHARED | COVERED | PORT | OBSOLETE | GAP | total |
|---|---:|---:|---:|---:|---:|---:|
| test_plugin_mem.py | 0 | 12 | 6 | 28 | 5 | 51 |
| test_plugin_memswap.py | 0 | 19 | 2 | 9 | 0 | 30 |
| test_plugin_load.py | 0 | 20 | 2 | 10 | 0 | 32 |
| test_plugin_cpu.py | 0 | 18 | 1 | 9 | 0 | 28 |
| test_plugin_percpu.py | 0 | 6 | 0 | 0 | 0 | 6 |
| test_plugin_quicklook.py | 0 | 12 | 3 | 2 | 0 | 17 |
| test_plugin_network.py | 0 | 25 | 2 | 11 | 1 | 39 |
| test_plugin_diskio.py | 0 | 25 | 2 | 13 | 1 | 41 |
| test_plugin_fs.py | 0 | 24 | 2 | 13 | 1 | 40 |
| test_cpu_percent.py | 0 | 0 | 1 | 0 | 0 | 1 |
| test_plugin_init_value.py | 0 | 1 | 0 | 1 | 0 | 2 |
| test_plugin_model.py | 0 | 0 | 0 | 2 | 0 | 2 |
| test_rate_on_list.py | 0 | 4 | 1 | 0 | 0 | 5 |
| test_hide_zero_threshold.py | 0 | 7 | 0 | 0 | 0 | 7 |
| test_hide_zero_row_visibility.py | 0 | 3 | 1 | 1 | 0 | 5 |
| test_network_hide_threshold.py | 0 | 5 | 0 | 0 | 0 | 5 |
| test_lazy_views.py | 0 | 1 | 0 | 6 | 0 | 7 |
| **total** | **0** | **182** | **23** | **105** | **8** | **318** |

#### PORT work, deduplicated (23 v4 tests → 13 v5 test additions)

1. `tests/test_plugin_mem_v5.py`: assert used, free, active, inactive, buffers, cached reach the payload (4 v4 tests).
2. New generic test over `main_v5.discover_plugin_classes()`: every `fields_description` entry has `description` + `unit` (5 v4 tests).
3. `tests/test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins`: add memswap, diskio, fs to the default-enabled subset (3).
4. `quicklook/model_v5.py::_collect_sync`: `load == round(load15 / cpu_count * 100, 1)` (1).
5. `quicklook/model_v5.py::_decorate_percpu`: `percpu_other` level distinct from cores/aggregate (`careful` at 60) (1).
6. `base_v5._compile_filter`: `hide=lo, docker.*` with a space (1).
7. `base_v5._read_alias`: spaces around commas stripped, internal spaces kept (1).
8. `network/model_v5.py`: per-direction levels parametrized (tx saturated/rx idle, both idle → ok) (2).
9. `diskio/model_v5.py`: level follows the rate, not a large lifetime counter (1).
10. `fs` alias on a mixed-case mount point (1).
11. `percpu/model_v5.py`: steal/guest_nice carried from their own attributes (1).
12. `base_v5._transform_gauge`: new item's third cycle measures its own delta (1).
13. `base_v5._compute_hide_zero`: row visible when only the second field moves (1).

#### GAPs (8 v4 tests → 6 distinct gaps)

1. mem `used = max(0, total - available)` and `percent` clamp [0,100] (LXC/cgroup-v2) not ported. v5 publishes psutil raw (3 tests).
2. mem ZFS ARC adjustment (#3979) not ported (1).
3. `[mem] available` config key not ported (parity inventory §11 ❌, undecided) (1).
4. network TUI rows not sorted (v4 natural sort by alias/name) (1).
5. diskio TUI rows sorted by raw name lexically, not natural and not by alias (1).
6. fs read-only mounts not exempted from thresholds (#3143). Divergence noted only in `tui-v4-rendering-patterns.md`, not decided in the decisions doc (1).

## v4 → v5 test migration audit — group 2

Branch `develop-v5`. Read-only audit. The whole group (290 pytest items, 261 test functions) passes today: `PYTHONPATH=. uv run pytest <files>`.

Conventions: `v5:` = `tests/<file>_v5.py::<test>`. "base" = `tests/test_plugin_base_v5.py`.
SHARED means the module under test is imported by a v5 model and runs unchanged. Some SHARED tests build their fixture with the v4 `glances.config.Config`. That module stays, because shared modules import it (`glances/web_list.py`, `containers/engines/{docker,lxd,podman}.py`).

**Caveat on mixed files.** Some files hold SHARED tests next to tests of the v4 plugin class. They import that class at module level:
- `test_plugin_sensors.py` imports `SensorsPlugin`.
- `test_plugin_containers.py` imports `ContainersPlugin`.
- `test_plugin_ports.py` imports `PortsPlugin`.
- `test_plugin_processcount.py` uses the `glances_stats` fixture.

When the v4 plugin classes are deleted, split these files and keep only the SHARED tests. Otherwise they fail at collection time.

---

### tests/test_plugin_sensors.py
v5 model `glances/plugins/sensors/model_v5.py` imports `GlancesGrabSensors` and `sensors_definition` from `glances.plugins.sensors`, and `GlancesGrabHDDTemp` and `GlancesGrabBat` from `sensor/*`. The v4 `SensorsPlugin` and `HddtempPlugin` classes are not used.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestSensorsPluginBasics::test_plugin_name | COVERED | test_plugin_sensors_v5.py::test_plugin_identity |
| TestSensorsPluginBasics::test_plugin_is_enabled | PORT | No v5 test says sensors is enabled by default. Assert `not PluginModel.DISABLED_BY_DEFAULT` and `not PluginModel.is_disabled(config)` in test_plugin_sensors_v5.py, or add `"sensors"` to the subset in test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins |
| TestSensorsPluginBasics::test_display_curse_enabled | COVERED | test_plugin_base_v5.py::test_display_in_tui_defaults_true (sensors does not override `DISPLAY_IN_TUI`) |
| TestSensorsPluginBasics::test_get_key_returns_label | COVERED | test_plugin_sensors_v5.py::test_plugin_identity (`_primary_key == "label"`) |
| TestSensorsPluginUpdate::test_update_returns_list | COVERED | test_plugin_sensors_v5.py::test_grab_stats_merges_all_types |
| TestSensorsPluginUpdate::test_each_sensor_has_label | COVERED | same |
| TestSensorsPluginUpdate::test_each_sensor_has_type | COVERED | same (`type` stamped by `_grab_typed`) |
| TestSensorsPluginUpdate::test_each_sensor_has_value | COVERED | same |
| TestSensorsPluginUpdate::test_each_sensor_has_unit | COVERED | same (unit comes from the shared grabbers) |
| TestSensorsPluginTypes::test_valid_sensor_types | COVERED | same (the four type constants) |
| TestSensorsPluginViews::test_update_views_creates_views | OBSOLETE | v4 views dict replaced by `_levels` (decisions §3.3) |
| TestSensorsPluginViews::test_views_keyed_by_label | OBSOLETE | v4 views; `_levels` keyed by label is asserted in test_plugin_sensors_v5.py::test_level_from_hardware_threshold |
| TestSensorsPluginJSON::test_get_stats_returns_json | OBSOLETE | v4 `get_stats()` returned a JSON string; v5 serialises through FastAPI routes (test_routes_v5.py) |
| TestSensorsPluginJSON::test_json_preserves_sensor_data | OBSOLETE | same; payload shape checked by base `test_collection_update_writes_data_envelope` |
| TestSensorsPluginReset::test_reset_clears_stats | OBSOLETE | v4 `reset()`/`get_init_value()` machinery does not exist in v5 (StatsStore per cycle, §1.3) |
| TestSensorsPluginReset::test_reset_views | OBSOLETE | v4 views |
| TestSensorsPluginFieldsDescription::test_fields_description_exists | COVERED | test_plugin_sensors_v5.py::test_fields_description_flags |
| TestSensorsPluginFieldsDescription::test_mandatory_fields_described | COVERED | same (label/type/unit/value) |
| TestSensorsPluginFieldsDescription::test_threshold_fields_described | COVERED | same (warning/critical) |
| TestSensorsPluginMsgCurse::test_msg_curse_returns_list | OBSOLETE | v4 msg_curse; replaced by `render_curses_v5.render` (test_plugin_sensors_render_curses_v5.py) |
| TestSensorsPluginMsgCurse::test_msg_curse_empty_without_max_width | OBSOLETE | v4 msg_curse `max_width` contract |
| TestSensorsPluginMsgCurse::test_msg_curse_without_args | COVERED | test_plugin_sensors_render_curses_v5.py::test_header_and_one_row (value "42" rendered) |
| TestSensorsPluginExport::test_get_export_returns_list | COVERED | test_plugin_base_v5.py::test_collection_get_export_returns_list |
| TestSensorsPluginExport::test_export_equals_raw | OBSOLETE | v5 `get_export()` drops internal fields by design (§7.2, #3211) |
| TestSensorsPluginRefresh::test_refresh_multiplier_applied | COVERED | test_scheduler_v5.py::test_plugin_default_refresh_time_beats_global (sensors declares `DEFAULT_REFRESH_TIME = 30`) |
| TestSensorsPluginBatteryTrend::test_battery_trend_charging | PORT | Assert `_battery_trend({"status": "Charging"}) == unicode_message("ARROW_UP")` in `glances/plugins/sensors/render_curses_v5.py` |
| TestSensorsPluginBatteryTrend::test_battery_trend_discharging | COVERED | test_plugin_sensors_render_curses_v5.py::test_battery_trend_arrow |
| TestSensorsPluginBatteryTrend::test_battery_trend_full | PORT | `_battery_trend({"status": "Full"}) == unicode_message("CHECK")` |
| TestSensorsPluginBatteryTrend::test_battery_trend_no_status | PORT | `_battery_trend({}) == ""` |
| TestSensorsPluginThresholds::test_sensor_warning_threshold | COVERED | test_plugin_sensors_v5.py::test_grab_stats_merges_all_types (warning kept, or defaulted to None) |
| TestSensorsPluginThresholds::test_sensor_critical_threshold | COVERED | same |
| TestSensorsPluginGrabMap::test_sensors_grab_map_exists | OBSOLETE | v4 `sensors_grab_map`; v5 `_build_grabbers` (test_plugin_sensors_v5.py::test_grabbers_are_built_on_first_collect) |
| TestGlancesGrabSensors::test_cpu_temp_sensor_init | SHARED | `GlancesGrabSensors` imported by sensors/model_v5.py |
| TestGlancesGrabSensors::test_fan_speed_sensor_init | SHARED | same |
| TestGlancesGrabSensors::test_sensor_update_returns_list | SHARED | same |
| TestSensorsPluginAlerts::test_views_have_value_decoration | COVERED | test_plugin_sensors_v5.py::test_level_from_hardware_threshold |
| TestSensorsPluginConfigThresholds::test_partial_type_thresholds_are_used | COVERED | test_plugin_sensors_v5.py::test_per_type_config_warning_only_is_honoured, ::test_per_type_config_beats_hardware (critical only), ::test_careful_tier_from_config |
| TestSensorsPluginConfigThresholds::test_partial_sensor_thresholds_are_used | COVERED | test_plugin_sensors_v5.py::test_per_sensor_config_careful_only_is_honoured |
| TestSensorsPluginConfigThresholds::test_config_thresholds_overwrite_system_ones | COVERED | test_plugin_sensors_v5.py::test_config_warning_only_does_not_borrow_the_hardware_critical, ::test_thresholds_resolved_from_single_coherent_tier |
| TestSensorsPluginConfigThresholds::test_system_thresholds_are_used_when_not_configured | COVERED | test_plugin_sensors_v5.py::test_level_hardware_warning |
| TestSensorsPluginConfigThresholds::test_no_threshold_at_all_is_not_decorated | COVERED | test_plugin_sensors_v5.py::test_level_none_when_no_critical |
| TestSensorsPluginZeroValue::test_battery_at_zero_percent_is_critical | PORT | `PluginModel._derived_parameters` with `battery_critical=90` and a battery row `value=0` must give level `critical`. No v5 test uses value 0 |
| TestSensorsPluginZeroValue::test_battery_at_zero_is_not_less_alarming_than_a_small_charge | PORT | same model: the level for 0 equals the level for 1/3/9 |
| TestSensorsPluginZeroValue::test_stopped_fan_is_evaluated_rather_than_skipped | PORT | same model: a fan_speed row `value=0` with fan thresholds gets a `_levels` entry |
| TestSensorsPluginZeroValue::test_absent_sensor_is_still_skipped | PORT | same model: `value=[]` and `value=None` give no `_levels` entry (only the renderer is tested today: test_empty_battery_skipped) |
| TestSensorsPluginZeroValue::test_placeholder_reading_does_not_raise | PORT | same model: `b'ERR'`, `b'SLP'` and `"ERR"` give no entry and do not raise |
| TestSensorsPluginZeroValue::test_nonzero_readings_are_unaffected | COVERED | test_plugin_sensors_v5.py::test_careful_tier_from_config |
| TestHddtempPlugin::test_refused_connect_is_not_retried | COVERED | test_plugin_sensors_v5.py::test_hddtemp_not_polled_again_after_failed_connect |
| TestHddtempPlugin::test_disabled_plugin_does_not_connect | COVERED | test_plugin_sensors_v5.py::test_hddtemp_disable_is_honoured |
| TestHddtempPlugin::test_host_and_port_come_from_the_hddtemp_section | COVERED | test_plugin_sensors_v5.py::test_hddtemp_reads_its_own_section |

### tests/test_plugin_gpu.py
`gpu/model_v5.py` builds the v4 card backends (`cards/{nvidia,amd,intel,arm}`). `tegra` is used by `cards/nvidia.py`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestArmFdinfoParser::* (7 tests: valid_panthor_record, not_a_drm_fd, empty_text, missing_driver_line, memory_default_unit_is_kib, unknown_memory_unit_ignored, malformed_lines_do_not_crash) | SHARED | `glances/plugins/gpu/cards/arm.py` |
| TestArmComputeHelpers::* (8 tests: compute_mem_percent_{none,zero_total,half,clamped,capacity_denominator,capacity_clamped}, get_device_name_{known,unknown}) | SHARED | cards/arm.py |
| TestArmMemCapacity::* (4 tests) | SHARED | cards/arm.py |
| TestArmBackendDiscovery::* (7 tests: device_enumeration, stats_shape, temperature, fan_speed_always_none, mem_aggregated_from_fdinfo, proc_first_call_is_none, proc_second_call_is_int) | SHARED | cards/arm.py `ArmGPU` |
| TestArmBackendNoHardware::test_missing_drm_root | SHARED | cards/arm.py |
| TestArmBackendNoHardware::test_missing_proc_root | SHARED | cards/arm.py |
| TestArmAggregation::test_aggregate_fdinfo_ignores_non_drm | SHARED | cards/arm.py |
| TestTegraBackend::* (7 tests) | SHARED | cards/tegra.py (via cards/nvidia.py) |
| TestGpuPluginIntegration::test_plugin_name | COVERED | test_plugin_gpu_v5.py::test_plugin_identity |
| TestGpuPluginIntegration::test_get_key_returns_gpu_id | COVERED | test_plugin_gpu_v5.py::test_plugin_identity (`_primary_key == "gpu_id"`) |
| TestGpuPluginIntegration::test_update_does_not_crash | COVERED | test_plugin_gpu_v5.py::test_grab_stats_survives_backend_failure, ::test_grab_stats_empty_when_no_backend |
| TestGpuPluginIntegration::test_exit_tolerates_none_backends | GAP | v5 `gpu/model_v5.py` does not override `stop()`, so the backends' `exit()` (nvmlShutdown and the other card cleanups) is never called on shutdown. `mpp/model_v5.py:104` does call it. NPU has the same gap. No decision drops it. Fix: add `stop()` that calls `exit()` on each backend inside try/except. Then test that `stop()` calls each backend's `exit()` and survives one that raises. Also test that `_build_backends` skips a constructor that raises (not tested today) |
| TestGpuPluginIntegration::test_arm_backend_can_be_injected | COVERED | test_plugin_gpu_v5.py::test_grab_stats_concatenates_backends (backends are injected through `_backends`) |

### tests/test_plugin_npu.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestNpuTemperatureAlert::test_a_hot_npu_is_alerted | COVERED | test_plugin_npu_v5.py::test_temperature_level_warning_at_75, ::test_temperature_critical_config_override_wins_over_default |
| TestNpuTemperatureAlert::test_each_threshold_boundary | COVERED | test_plugin_npu_v5.py::test_npu_temperature_thresholds_mirror_v4 (60/70/80 ladder) plus test_thresholds_v5.py::test_compute_level_high_direction (inclusive boundaries) |
| TestNpuTemperatureAlert::test_the_curses_line_reads_the_decoration_that_is_written | COVERED | test_plugin_npu_render_curses_v5.py::test_temperature_critical_level_coloured |
| TestNpuTemperatureAlert::test_a_card_that_reports_no_temperature_keeps_a_view_without_a_decoration | PORT | `npu/model_v5.py` `_derived_parameters`: a row with `temperature: None` (AMD/Rockchip) gets no `temperature` level. Base skips None (`base_v5.py:1099`), but no test asserts it |
| TestNpuTemperatureAlert::test_the_other_fields_still_carry_their_own_alerts | PORT | Same model: `load=95` → `critical`, `freq=10` → `ok`, `temperature=20` → `ok` in one pass. No v5 NPU test covers load or freq levels |
| TestShippedNpuLimits::test_the_npu_section_defines_a_temperature_threshold | COVERED | test_plugin_npu_v5.py::test_npu_temperature_thresholds_mirror_v4 (v5 ships the defaults in `fields_description`) |
| TestShippedNpuLimits::test_the_npu_thresholds_match_the_gpu_ones | COVERED | test_plugin_npu_v5.py::test_npu_temperature_thresholds_mirror_v4 + test_plugin_gpu_v5.py::test_gpu_temperature_thresholds_mirror_v4 (both 60/70/80) |

### tests/test_plugin_smart.py
`smart/model_v5.py` imports the v4 module (`get_smart_data`, `import_error_tag`).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestSmartHideAttributes::test_a_plain_list_is_honoured | COVERED | test_plugin_smart_v5.py::test_grab_passes_hide_attributes_to_helper |
| TestSmartHideAttributes::test_whitespace_around_items_is_ignored | COVERED | test_plugin_smart_v5.py::test_hide_attributes_ignores_whitespace_around_items |
| TestSmartHideAttributes::test_an_empty_value_hides_nothing | PORT | `PluginModel(...)._hide_attributes == []` for `hide_attributes=` (empty) and when the key is absent (`_parse_hide_attributes`) |
| test_top_level_key_is_not_rendered_as_an_attribute | OBSOLETE | v4 `_get_sorted_stat_keys` and the top-level `key` injected by v4 `update()` (#3704). v5 `_reshape` builds `attributes` from `get_smart_data` output, which has no top-level `key`. Ordering is covered by test_grab_reshapes_numeric_keys_to_attributes_list |
| test_msg_curse_renders_the_device_attributes | COVERED | test_plugin_smart_render_curses_v5.py::test_header_device_and_attributes |
| test_missing_smartctl_returns_no_device | SHARED | `glances.plugins.smart.get_smart_data` (called by model_v5) |

### tests/test_plugin_wifi.py
v5 has its own `_derived_parameters` (`compute_level`, direction `low`). The defaults (-65/-75/-85) are always applied.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestWifiAlertThresholds::test_all_levels_configured | COVERED | test_plugin_wifi_v5.py::test_level_ok / _careful / _warning / _critical (same -50/-70/-80/-90 values) |
| TestWifiAlertThresholds::test_only_careful_still_alerts | COVERED | test_plugin_wifi_v5.py::test_level_careful. In v5 a partial config is filled from the defaults, so the v4 TypeError path cannot exist |
| TestWifiAlertThresholds::test_only_warning_still_alerts | COVERED | test_plugin_wifi_v5.py::test_level_warning |
| TestWifiAlertThresholds::test_only_critical_still_alerts | COVERED | test_plugin_wifi_v5.py::test_level_critical |
| TestWifiAlertThresholds::test_a_good_signal_is_ok_under_any_partial_config | COVERED | test_plugin_wifi_v5.py::test_level_ok |
| TestWifiAlertThresholds::test_the_most_severe_level_wins | COVERED | test_plugin_wifi_v5.py::test_level_critical, ::test_level_boundary_is_inclusive |
| TestWifiAlertThresholds::test_no_threshold_at_all_is_not_decorated | GAP (low) | v5 `_read_thresholds` always falls back to the code defaults, so wifi colouring and alerts cannot be turned off by leaving the thresholds unset. No decision records this (parity inventory §17 only says the semantics are kept). Probably acceptable: record a decision, or treat it as an intentional divergence |
| TestWifiAlertThresholds::test_a_non_numeric_level_is_not_decorated | COVERED | test_plugin_wifi_v5.py::test_level_none_skipped (model) + test_plugin_wifi_render_curses_v5.py::test_skip_non_numeric_quality_level |

### tests/test_plugin_ports.py
`ports/model_v5.py` reuses `ThreadScanner`, `GlancesPortsList` and `GlancesWebList`. The alert level is reimplemented in `_port_level` and `_web_level`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestPortsPluginAlertLevel::test_most_severe_condition_wins | COVERED | test_plugin_ports_v5.py::test_web_level_critical_outranks_warning (#3632) |
| TestPortsPluginAlertLevel::test_web_not_scanned_yet_is_careful | COVERED | test_plugin_ports_v5.py::test_web_level_none_status_is_careful |
| TestPortsPluginAlertLevel::test_web_failing_and_slow_is_critical | COVERED | test_plugin_ports_v5.py::test_web_level_critical_outranks_warning |
| TestPortsPluginAlertLevel::test_web_failing_and_fast_is_critical | COVERED | test_plugin_ports_v5.py::test_web_level_bad_http_code_is_critical |
| TestPortsPluginAlertLevel::test_web_ok_but_slow_is_warning | COVERED | test_plugin_ports_v5.py::test_web_level_slow_response_is_warning |
| TestPortsPluginAlertLevel::test_web_ok_and_fast_is_ok | COVERED | test_plugin_ports_v5.py::test_web_level_ok_codes_are_ok |
| TestIcmpPingCommand::test_windows_timeout_is_expressed_in_milliseconds | SHARED | `ThreadScanner._port_scan_icmp` |
| TestIcmpPingCommand::test_linux_timeout_stays_in_seconds | SHARED | same |
| TestIcmpPingCommand::test_macos_timeout_stays_in_seconds | SHARED | same |
| TestIcmpPingCommand::test_timeout_is_not_sent_through_the_name_resolver | SHARED | same |
| TestTcpScanSocket::test_the_timeout_is_set_on_the_scanning_socket | SHARED | `ThreadScanner._port_scan_tcp` |
| TestTcpScanSocket::test_scanning_does_not_change_the_process_wide_default_timeout | SHARED | same |
| TestTcpScanSocket::test_a_socket_that_cannot_be_created_is_reported_not_raised | SHARED | same |
| TestTcpScanSocket::test_a_closed_port_is_still_reported_offline | SHARED | same |

### tests/test_plugin_containers.py
`containers/model_v5.py` reuses the engines (`DockerEngineMonitor`/`DockerStatsFetcher`, Podman, LXD).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestDockerNetworkStatsAggregation::test_single_interface | SHARED | engines/docker.py `DockerStatsFetcher._get_network_stats` |
| TestDockerNetworkStatsAggregation::test_two_interfaces_are_summed | SHARED | same |
| TestDockerNetworkStatsAggregation::test_loopback_is_excluded | SHARED | same |
| TestDockerNetworkStatsNoData::test_host_network_returns_none | SHARED | same |
| TestDockerNetworkStatsNoData::test_empty_networks_returns_none | SHARED | same |
| TestDockerNetworkStatsNoData::test_all_interfaces_malformed_returns_none | SHARED | same |
| TestDockerNetworkStatsNoData::test_one_malformed_among_two_keeps_the_valid_one | SHARED | same |
| TestDockerNetworkStatsRates::test_rates_use_the_summed_counters | SHARED | same |
| TestDockerNetworkStatsRates::test_first_sample_has_no_rate_keys | SHARED | same |
| TestContainersTitle::test_several_engines_do_not_repeat_the_sort_fragment | OBSOLETE | Duplication bug in v4 `build_title`. The v5 renderer has no title builder; the sort is shown by the header underline (test_plugin_containers_render_curses_v5.py::test_sort_underline_on_cpu) |
| TestContainersTitle::test_several_engines_with_one_container_do_not_repeat_the_title | OBSOLETE | same; with several engines the Engine column is shown (test_engine_column_only_when_multiple_engines) |
| TestContainersTitle::test_one_engine_still_names_it | GAP | v5 `containers/render_curses_v5.py` has no `CONTAINERS N … (served by <engine>)` title line. With a single engine the engine name and the container count are shown nowhere. No decision found |
| TestContainersTitle::test_one_engine_one_container | GAP | same (no "(served by docker)") |
| TestContainersTitle::test_the_sort_key_is_named_in_the_title | COVERED | test_plugin_containers_render_curses_v5.py::test_sort_underline_on_name, ::test_sort_underline_on_mem_maps_to_memory_percent (sort key shown by underline) |
| TestContainersTitle::test_no_fragment_appears_twice | OBSOLETE | v4 `build_title` bug |
| test_parse_urls | COVERED | test_plugin_containers_v5.py::test_parse_urls_from_config, ::test_parse_urls_from_list |
| TestContainersMonitors::test_init_monitors_with_custom_urls | COVERED | test_plugin_containers_v5.py::test_init_monitors_with_custom_urls |
| TestContainersMonitors::test_init_monitors_all_disabled | COVERED | test_plugin_containers_v5.py::test_init_monitors_all_disabled |
| TestContainersMonitors::test_update_aggregates_stats_across_monitors | COVERED | test_plugin_containers_v5.py::test_grab_merges_engines_and_injects_engine_field, ::test_grab_aggregates_multiple_monitors_for_same_engine |
| TestContainersMonitors::test_exit_stops_all_monitors | COVERED | test_plugin_containers_v5.py::test_stop_calls_each_monitor |

### tests/test_plugin_containers_views.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestContainerDecorationViews::test_cpu_and_mem_views_exist_for_each_container | COVERED | test_plugin_containers_v5.py::test_cpu_level_uses_cpu_prefix_thresholds, ::test_mem_level_uses_mem_prefix_thresholds |
| TestContainerDecorationViews::test_a_container_over_its_threshold_is_not_left_plain | PORT | The model levels are covered (above) and the CPU cell colour is covered (render ::test_cpu_cell_coloured_by_level). No test checks the **MEM cell** colour from the `memory_percent` level. Add a render test against `containers/render_curses_v5._cpu_mem_cells` |
| TestContainerDecorationViews::test_the_view_is_keyed_by_container_name | COVERED | test_plugin_containers_v5.py::test_identity (`_primary_key == "name"`), ::test_per_container_cpu_override |
| TestContainerDecorationViews::test_a_container_without_cpu_or_memory_stats_still_has_a_decoration | PORT | A restarting container (no `cpu_percent` / `memory_percent`, `memory={}`) must not raise in `_reconcile_memory` / `_derived_parameters`, gets no cpu/mem level, and still renders a row (`containers/model_v5.py` + render) |

### tests/test_plugin_docker.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_list_is_sparse | SHARED | engines/docker.py `DockerEngineMonitor` |
| test_containers_are_inspected_every_cycle | SHARED | same |
| test_image_is_cached_across_cycles | SHARED | same |
| test_image_field_format_preserved | SHARED | same |
| test_engine_url_in_stats | SHARED | same (credentials in engine_url redacted through `glances.config.secure_option`) |
| test_connect_with_url | SHARED | same |
| test_image_cache_evicts_removed_containers | SHARED | same |

### tests/test_plugin_lxd.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestLxdStatsFetcher::* (8 tests: no_state_returns_empty, first_poll_returns_zero_cpu, second_poll_computes_cpu_delta, network_excludes_loopback, memory_unlimited_falls_back_to_peak, cpu_limit_explicit, cpu_limit_fallback, stop_terminates_thread) | SHARED | engines/lxd.py |
| TestLxdEngineMonitorGenerateStats::* (6 tests: stopped_instance_returns_minimal_stats, url_in_stats, running_instance_with_fetcher, proxy_device_ports, no_proxy_devices_empty_ports, image_from_config) | SHARED | engines/lxd.py |
| TestLxdEngineMonitorUpdate::* (6 tests: filters_to_running_only, all_tag_includes_stopped, cluster_filters_to_local_node, standalone_does_not_filter_by_location, cleans_up_removed_instances, disabled_returns_empty) | SHARED | engines/lxd.py |
| TestLxdEngineMonitorConnect::test_standalone_leaves_local_node_unset | SHARED | engines/lxd.py |
| TestLxdEngineMonitorConnect::test_cluster_sets_local_node | SHARED | engines/lxd.py |

### tests/test_plugin_virsh_injection.py (security, CVE-2026-46606)
`vms/model_v5.py` imports `glances.plugins.vms.engines.virsh.VmExtension` unchanged, so the fix is the same code path.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestUpdateStatsInjectionCanary::test_double_ampersand_injection_blocked | SHARED | engines/virsh.py `update_stats` |
| TestUpdateStatsInjectionCanary::test_pipe_injection_blocked | SHARED | same |
| TestUpdateStatsInjectionCanary::test_redirect_injection_blocked | SHARED | same |
| TestUpdateTitleInjectionCanary::test_double_ampersand_injection_blocked | SHARED | engines/virsh.py `update_title` |
| TestUpdateTitleInjectionCanary::test_pipe_injection_blocked | SHARED | same |
| TestUpdateTitleInjectionCanary::test_redirect_injection_blocked | SHARED | same |
| TestArgumentShape::test_update_stats_passes_domain_as_single_arg | SHARED | same |
| TestArgumentShape::test_update_title_passes_domain_as_single_arg | SHARED | same |

### tests/test_vms_decorations.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_a_column_reaches_critical_from_its_own_threshold (cpu/mem/load) | PORT | cpu → test_plugin_vms_v5.py::test_cpu_critical_level; mem → ::test_mem_level_uses_mem_prefix_thresholds. **No v5 model test checks a `load_1min` level** with `[vms] load_*` set (only `test_load_none_produces_no_level`). Add `load_critical=500`, `load_1min=600` → `critical` and `10` → `ok` in `vms/model_v5.py` |
| test_memory_is_measured_against_that_vm_own_total | COVERED | test_plugin_vms_v5.py::test_memory_percent_computed_from_usage_and_total + ::test_mem_level_uses_mem_prefix_thresholds |
| test_a_missing_value_is_left_alone_rather_than_read_as_zero | COVERED | test_plugin_vms_v5.py::test_load_none_produces_no_level |
| test_a_vm_with_no_memory_total_does_not_divide_by_zero | COVERED | test_plugin_vms_v5.py::test_memory_percent_none_when_total_zero |
| test_cpu_count_stays_uncoloured | COVERED | test_plugin_vms_v5.py::test_fields_description (watched set is exactly cpu_time/memory_percent/load_1min) |
| test_no_configured_thresholds_leaves_the_table_as_it_was | COVERED | test_plugin_vms_v5.py::test_no_threshold_configured_no_level_produced |
| test_a_per_vm_override_wins_over_the_shared_threshold | COVERED | test_plugin_vms_v5.py::test_per_vm_mem_override |

### tests/test_plugin_processcount.py
`processcount/model_v5.py` drives the shared `glances.processes.glances_processes`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestProcesscountPluginBasics::test_plugin_name | COVERED | test_plugin_processcount_v5.py::test_plugin_identity |
| TestProcesscountPluginBasics::test_plugin_is_enabled | PORT | Assert that processcount is enabled by default (`DISABLED_BY_DEFAULT` False, `is_disabled(config)` False), or add it to test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins |
| TestProcesscountPluginBasics::test_display_curse_enabled | COVERED | test_plugin_base_v5.py::test_display_in_tui_defaults_true |
| TestProcesscountPluginBasics::test_history_items_defined | COVERED | test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list |
| TestProcesscountPluginUpdate::test_update_returns_dict | COVERED | test_history_v5.py::test_a_real_cycle_publishes_numbers_for_every_historised_field[processcount] (real host) |
| TestProcesscountPluginUpdate::test_update_contains_total | COVERED | same |
| TestProcesscountPluginUpdate::test_total_positive | PORT | Real-host v5 cycle: `payload["total"] > 0` (`processcount/model_v5.PluginModel.update`) |
| TestProcesscountPluginUpdate::test_running_present | COVERED | test_history_v5.py::test_a_real_cycle_publishes_numbers_for_every_historised_field[processcount] |
| TestProcesscountPluginUpdate::test_sleeping_present | COVERED | same |
| TestProcesscountPluginUpdate::test_thread_count_present | COVERED | same |
| TestProcesscountPluginValues::test_counts_non_negative | PORT | Same real-host v5 cycle: every count >= 0 |
| TestProcesscountPluginValues::test_running_sleeping_less_than_total | PORT | same: `running + sleeping <= total` |
| TestProcesscountPluginValues::test_thread_count_reasonable | PORT | same: `thread >= total` |
| TestProcesscountPluginViews::test_update_views_returns_dict | OBSOLETE | v4 views (§3.3) |
| TestProcesscountPluginJSON::test_get_stats_returns_json | OBSOLETE | v4 JSON-string `get_stats` |
| TestProcesscountPluginJSON::test_json_contains_expected_fields | COVERED | test_plugin_processcount_v5.py::test_update_calls_engine_and_surfaces_count |
| TestProcesscountPluginHistory::test_history_enable_check | OBSOLETE | v4 per-plugin `history_enable()`. v5 has a global history store (test_history_v5.py::test_a_disabled_history_is_no_store_at_all) |
| TestProcesscountPluginHistory::test_get_items_history_list | COVERED | test_history_v5.py::test_the_historised_fields_are_v4s_items_history_list |
| TestProcesscountPluginReset::test_reset_clears_stats | OBSOLETE | v4 `reset()`/`get_init_value()` |
| TestProcesscountPluginReset::test_reset_views | OBSOLETE | v4 views |
| TestProcesscountPluginFieldsDescription::test_fields_description_exists | COVERED | test_plugin_processcount_v5.py::test_schema_fields |
| TestProcesscountPluginFieldsDescription::test_mandatory_fields_described | COVERED | same |
| TestProcesscountPluginFieldsDescription::test_field_has_description | PORT | Best as one generic test: every v5 `PluginModel.fields_description` field has `description`, looping over `main_v5.discover_plugin_classes()` (they all pass today) |
| TestProcesscountPluginFieldsDescription::test_field_has_unit | PORT | same generic test, for `unit` |
| TestProcesscountPluginMsgCurse::test_msg_curse_with_args | COVERED | test_plugin_processcount_render_curses_v5.py::test_render_produces_one_row |
| TestProcesscountPluginMsgCurse::test_msg_curse_format_with_args | COVERED | test_plugin_processcount_render_curses_v5.py::test_render_title_is_tasks_header |
| TestProcesscountPluginMsgCurse::test_msg_curse_content_with_args | COVERED | test_plugin_processcount_render_curses_v5.py::test_render_contains_aggregate_counts |
| TestProcesscountPluginExport::test_get_export_returns_dict | COVERED | test_plugin_base_v5.py::test_scalar_get_export_strips_internals_and_levels |
| TestProcesscountPluginExport::test_export_equals_raw | OBSOLETE | v5 export drops internal fields by design (§7.2); see test_plugin_processcount_v5.py::test_the_sort_key_is_not_exported |
| TestProcesscountPluginExtended::test_enable_extended_method_exists | OBSOLETE | v4 plugin API. Extended stats moved to the processlist `e` hotkey (decisions §10, "Shipped (b3)") |
| TestProcesscountPluginExtended::test_disable_extended_method_exists | OBSOLETE | same |
| TestProcesscountPluginPidMax::test_pid_max_in_fields_description | COVERED | test_plugin_processcount_v5.py::test_schema_fields |
| TestProcesscountPluginPidMax::test_pid_max_description | PORT | Folded into the generic description test above |
| TestProcessesUpdateProcesscount::test_pid_max_is_not_overwritten_by_the_status_count | SHARED | `glances.processes.GlancesProcesses.update_processcount` |
| TestProcessesUpdateProcesscount::test_status_count_uses_equality | SHARED | same |
| TestProcessesCount::test_processes_count_none_max_processes | SHARED | `GlancesProcesses.processes_count` |
| TestProcessesCount::test_processes_count_does_not_raise_with_max_processes | SHARED | same |

### tests/test_connections_states.py
`connections/model_v5.py` is a standalone rewrite (it imports psutil only).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_terminated_states_are_counted | GAP | The `terminated` sum is covered (test_plugin_connections_v5.py::test_terminated_computed_from_terminated_states_not_initiated). The per-state counters (`TIME_WAIT`, `CLOSE_WAIT`, …) that v4 publishes (`connections/__init__.py:126-133`) are neither computed nor declared in v5, so they are missing from `/api/5/connections` and from exports. No decision drops them |
| test_initiated_states_are_counted | GAP | `initiated` is covered; the per-state `SYN_SENT`/`SYN_RECV` counters are missing in v5 (same gap) |
| test_every_terminated_state_is_reported | GAP | same gap: none of `terminated_states` is a key in the v5 payload |
| test_listen_and_established_are_counted | COVERED | test_plugin_connections_v5.py::test_terminated_computed_from_terminated_states_not_initiated (LISTEN / ESTABLISHED) |
| test_conntrack_alert_reads_the_tracked_percentage | COVERED | test_plugin_connections_v5.py::test_nf_conntrack_percent_default_thresholds_drive_level |
| test_conntrack_alert_stays_ok_below_the_first_threshold | COVERED | same (`(10, 100, "ok")`) |
| test_failed_conntrack_probe_is_not_retried | OBSOLETE | Intentional divergence. v5 retries every cycle so the probe can self-heal, and logs the warning once. Rationale is in the `connections/model_v5.py` docstring §1, which explicitly reverses v4 `4591a6f5`. Covered by ::test_nf_conntrack_failure_is_retried_next_cycle and ::test_repeated_failure_warns_only_once. The decision is recorded only in that docstring; consider adding it to decisions.md |
| test_failed_net_connections_probe_is_not_retried | OBSOLETE | same; ::test_net_connections_failure_is_retried_next_cycle |
| test_working_probes_keep_running | COVERED | test_plugin_connections_v5.py::test_net_connections_failure_is_retried_next_cycle (called every cycle) + ::test_nf_conntrack_percent_default_thresholds_drive_level (percent read from the files) |

### tests/test_ip_response_validation.py
v5 `ip/model_v5.py` replaces `ThreadPublicIpAddress` with an in-model fetch and does not import the v4 module.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_invalid_response_preserves_last_public_info (7 payloads) | GAP (bug) | When the body is not a JSON object, `_fetch_public_ip_info` returns `{}`, not `self._public_cache`. `_grab_stats` then assigns that result to `_public_cache`, so one malformed response (`[]`, `"error"`, `42`, `true`, `null`) **wipes the last good public IP**. v4 keeps it. test_plugin_ip_v5.py::test_fetch_ignores_a_non_object_response only checks for no crash, with an empty cache. Fix: return `self._public_cache` on a non-object body. Then test with a pre-filled cache |
| test_valid_response_updates_public_info | COVERED | test_plugin_ip_v5.py::test_fetch_uses_basic_auth_when_credentials_set (returns the parsed dict), ::test_public_fetch_merges |

### tests/test_ports_no_credential_leak.py (security, GHSA-2jqf-3j6f-683p)
`GlancesWebList` and `ThreadScanner` are reused verbatim. v5 also has an end-to-end mirror in `tests/test_ports_no_credential_leak_v5.py`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_no_secret_anywhere_in_the_published_list | SHARED | `glances/web_list.py`. Also v5 end-to-end: test_ports_no_credential_leak_v5.py::test_payload_carries_no_credential |
| test_published_url_is_redacted | SHARED | web_list.py (+ v5 ::test_published_url_is_redacted) |
| test_proxies_are_not_published | SHARED | web_list.py (+ v5 ::test_proxies_stay_out_of_the_payload) |
| test_default_description_drops_the_userinfo | SHARED | web_list.py (+ v5 ::test_default_description_drops_the_userinfo) |
| test_default_description_keeps_the_port | SHARED | web_list.py |
| test_explicit_description_is_untouched | SHARED | web_list.py |
| test_credentialless_url_is_published_verbatim | SHARED | web_list.py (+ v5 ::test_credentialless_url_is_published_verbatim) |
| test_scanner_still_gets_the_real_url_and_proxies | SHARED | web_list.py `get_web_secrets` |
| test_no_proxy_configured_stays_none | SHARED | same |
| test_scan_requests_the_real_url_not_the_redacted_one | SHARED | `ThreadScanner._web_scan` (+ v5 ::test_scan_requests_the_real_url_not_the_redacted_one) |

### tests/test_web_list_ssl_verify.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_ssl_verify_false_is_a_boolean | SHARED | web_list.py (also mirrored in test_web_list_ssl_verify_v5.py) |
| test_ssl_verify_true_is_a_boolean | SHARED | same |
| test_ssl_verify_keeps_a_ca_bundle_path | SHARED | same |
| test_ssl_verify_defaults_to_true | SHARED | same |

### tests/test_folder_list_isolation.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_configured_folder_lists_are_independent | SHARED | `glances/folder_list.FolderList` (folders/model_v5.py:42, :76) |

### tests/test_folder_list_refresh.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_folder_is_not_walked_again_before_its_refresh_delay | SHARED | folder_list.py |
| test_folder_is_walked_again_once_the_timer_is_over | SHARED | same |
| test_the_timer_is_restarted_after_a_walk | SHARED | same |
| test_a_folder_without_a_timer_is_still_updated | SHARED | same |

---

### Summary (counts are test functions; grouped `::*` rows are counted per function)

| v4 file | SHARED | COVERED | PORT | OBSOLETE | GAP | total |
|---|---|---|---|---|---|---|
| test_plugin_sensors.py | 3 | 28 | 9 | 10 | 0 | 50 |
| test_plugin_gpu.py | 36 | 4 | 0 | 0 | 1 | 41 |
| test_plugin_npu.py | 0 | 5 | 2 | 0 | 0 | 7 |
| test_plugin_smart.py | 1 | 3 | 1 | 1 | 0 | 6 |
| test_plugin_wifi.py | 0 | 7 | 0 | 0 | 1 | 8 |
| test_plugin_ports.py | 8 | 6 | 0 | 0 | 0 | 14 |
| test_plugin_containers.py | 9 | 6 | 0 | 3 | 2 | 20 |
| test_plugin_containers_views.py | 0 | 2 | 2 | 0 | 0 | 4 |
| test_plugin_docker.py | 7 | 0 | 0 | 0 | 0 | 7 |
| test_plugin_lxd.py | 22 | 0 | 0 | 0 | 0 | 22 |
| test_plugin_virsh_injection.py | 8 | 0 | 0 | 0 | 0 | 8 |
| test_vms_decorations.py | 0 | 6 | 1 | 0 | 0 | 7 |
| test_plugin_processcount.py | 4 | 17 | 8 | 8 | 0 | 37 |
| test_connections_states.py | 0 | 4 | 0 | 2 | 3 | 9 |
| test_ip_response_validation.py | 0 | 1 | 0 | 0 | 1 | 2 |
| test_ports_no_credential_leak.py | 10 | 0 | 0 | 0 | 0 | 10 |
| test_web_list_ssl_verify.py | 4 | 0 | 0 | 0 | 0 | 4 |
| test_folder_list_isolation.py | 1 | 0 | 0 | 0 | 0 | 1 |
| test_folder_list_refresh.py | 4 | 0 | 0 | 0 | 0 | 4 |
| **Total** | **117** | **89** | **23** | **24** | **8** | **261** |

## v4 → v5 test migration audit — group 3

Branch `develop-v5`. Read-only analysis. All 13 v4 files pass today (`222 passed`).

### What v5 shares with v4 (verified from the imports)

| Shared v4 module | v5 call site |
|---|---|
| `glances.secure.secure_popen` | `glances/actions_v5/shell/__init__.py` (`from glances.secure import secure_popen`, called in `ShellAction.execute` with `allow_operators=`, `timeout=`, `render=partial(chevron.render, data=context)`); indirectly through `glances.amps.default` |
| `glances.amps.default.Amp`, `glances.amps.amp.GlancesAmp` | `glances/amps_list_v5.py` (`_DEFAULT_MODULE = "glances.amps.default"`, `module.Amp(name=name, args=self._args)` with `self._args = SimpleNamespace(disable_config_exec=...)`) |
| `glances.processes` (`GlancesProcesses`, `glances_processes`, `sort_stats`, …) | `processcount/processlist/programlist model_v5`, `alerts_v5`, `amps_list_v5`, `main_v5`, `glances_curses_v5` |
| `glances.programs.processes_to_programs` | imported by `glances/processes.py:24`, used by `get_list(as_programs=True)` (`programlist/model_v5.py:178`) |
| `glances.filter` | imported by v5 (`GlancesFilter`), and `GlancesFilterList` through `glances.processes` |
| `glances.globals` | `split_esc` (`plugins/plugin/base_v5.py`), `auto_unit` (many renderers), `subsample` (`exports/glances_graph/export_v5.py`), `get_ip_address` (`ip/model_v5.py`, `zeroconf_v5.py`), `pretty_date` and `string_value_to_float` (shared container engines docker/lxd/podman) |
| `glances.outputs.glances_bars.Bar` | 2 v5 modules |
| NPU/MPP card drivers | `npu/model_v5.py:41-45` (`AmdNPU`, `IntelNPU`, `RockchipNPU`); `mpp/model_v5` (`RockchipMPP`) |

**v4-only (not imported by v5 code):** `glances.actions` (`GlancesActions`, `_sanitize_mustache_dict`), `glances.stats`, `glances.main`, `glances.events_list`, `glances.thresholds`, `glances.attribute`, `glances.history`, `glances.plugins.plugin.model`/`dag`, `glances.plugins.fs.zfs`, `glances.outputs.glances_json_serializer`.

**Before you delete anything:** two files mix SHARED tests with v4-only module-level imports.
- `tests/test_core.py` imports `GlancesMain`, `GlancesStats`, `GlancesEventsList`, `glances.thresholds`, `GlancesPluginModel` and the v4 `NpuPlugin`/`MppPlugin` at module level. It also builds a `GlancesStats` at import time. Its 7 SHARED tests have to move to a v4-free file, or they stop running.
- `tests/test_actions_sanitize.py` imports `glances.actions` at module level. Its 8 SHARED `secure_popen` tests (`TestSecurePopen`, `TestSecurePopenRender`) have to move too, for example into `tests/test_secure_popen.py`.

---

### tests/test_core.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_000_update | OBSOLETE | Drives v4 `GlancesStats.update()`. v5 collects through the scheduler and real cycles: `tests/test_scheduler_v5.py::test_smoke_two_plugins_write_to_store`, `tests/test_history_v5.py::test_a_real_cycle_publishes_numbers_for_every_historised_field` (real psutil, 10 plugins). |
| test_001_plugins | PORT | `tests/test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins` checks only `{cpu, mem, load, network, percpu}`. Extend the set to v4's mandatory list (`system, cpu, load, mem, memswap, network, diskio, fs`) against `glances.main_v5.discover_plugins`. |
| test_002_system | COVERED | `tests/test_plugin_system_v5.py::test_update_collects_linux_system_info` (hostname, os_name) |
| test_003_cpu | COVERED | `tests/test_plugin_cpu_v5.py::test_update_writes_aggregate_fields` (user/system/idle) |
| test_004_load | COVERED | `tests/test_plugin_load_v5.py::test_update_writes_loadavg_to_store` (min1/5/15, cpucore) |
| test_005_mem | COVERED | `tests/test_plugin_mem_v5.py::test_update_writes_psutil_fields_to_store` |
| test_006_memswap | COVERED | `tests/test_plugin_memswap_v5.py::test_update_writes_swap_fields` |
| test_007_network | COVERED | `tests/test_plugin_network_v5.py::test_grab_stats_returns_one_dict_per_interface` |
| test_008_diskio | COVERED | `tests/test_plugin_diskio_v5.py::test_update_yields_one_entry_per_disk` |
| test_009_fs | COVERED | `tests/test_plugin_fs_v5.py::test_update_yields_one_entry_per_partition` |
| test_010_processes | COVERED | `tests/test_plugin_processcount_v5.py::test_update_calls_engine_and_surfaces_count`, `tests/test_plugin_processlist_v5.py::test_update_surfaces_engine_list` |
| test_010a_processes_cpu_num | GAP | The engine half (`glances_processes.disable_cpu_num`, `get_displayed_attr`) is shared. The display half is not in v5: `processlist/model_v5.py:133` publishes `cpu_num`, but `processlist/render_curses_v5.py` `_FIXED_COL_KEYS` has no CPU# column and no v5 Web UI component renders it. Yet `o` (sort by cpu_num) is ported (`glances_curses_v5.py:235`), so you can sort by a column you cannot see. No decision drops the column. |
| test_010c_processlist_sum_stats_indexes_lists | COVERED | v5 `render_curses_v5.summarise` reads `io_counters` by position through `_io_rate`: `tests/test_plugin_processlist_render_curses_v5.py::test_summarise_ignores_an_unknown_io_rate`, `::test_summarise_adds_up_the_columns_that_matter` |
| test_010b_processes_nice_windows_labels | COVERED | `tests/test_plugin_processlist_render_curses_v5.py::test_render_nice_shows_windows_priority_class_as_a_label`, `::test_render_nice_keeps_an_unmapped_windows_value_numeric`, `::test_render_nice_shows_the_raw_value_on_posix`, `::test_render_nice_cell_keeps_its_level_colour_on_windows` |
| test_011_folders | COVERED | `tests/test_plugin_folders_v5.py::test_single_folder_collected` |
| test_012_ip | COVERED | `tests/test_plugin_ip_v5.py::test_grab_private_merges_address` |
| test_013_irq | COVERED | `tests/test_plugin_irq_v5.py::test_grab_stats_returns_cumulative_counters` |
| test_014_gpu | COVERED | `tests/test_plugin_gpu_v5.py::test_grab_stats_concatenates_backends` |
| test_015_sorted_stats | GAP | v4 `GlancesPluginModel.sorted_stats()` sorts network and diskio rows by alias-or-key, in natural (numeric-aware) order (`network/__init__.py:323`, `diskio/__init__.py:257`). In v5, `network/render_curses_v5.py` does not sort at all (psutil order), and `diskio/render_curses_v5.py:169` sorts on the raw `disk_name`, lexicographically, ignoring the alias. No decision covers this. |
| test_016_subsample | SHARED | `glances.globals.subsample` (used by `exports/glances_graph/export_v5.py`). Move out of test_core. |
| test_017_hddsmart | COVERED | `tests/test_plugin_smart_v5.py::test_grab_empty_when_not_root` |
| test_017_programs | COVERED | `tests/test_plugin_programlist_v5.py::test_update_surfaces_engine_programs` |
| test_018_string_value_to_float | SHARED | `glances.globals` (used by the shared podman engine). Move out of test_core. |
| test_019_events | OBSOLETE | v4 `GlancesEventsList` is replaced by `GlancesAlerts`' transition-event model (decisions §3.4). The `min_duration` debounce is covered by `tests/test_alerts_v5.py::test_hysteresis_holds_back_first_observation`, `::test_immediate_commit_when_min_duration_is_zero`. **Caveat:** `min_interval` event merging and the per-event min/max/count aggregates are recorded only as "❌ absent" in parity-inventory §33. There is no explicit drop decision, so the maintainer should confirm. |
| test_020_filter | SHARED | `glances.filter` (`GlancesFilter` imported by v5, `GlancesFilterList` through `glances.processes`). Move out of test_core. |
| test_021_pretty_date | SHARED | `glances.globals.pretty_date` (shared container engines). Move out of test_core. |
| test_022_plugin_dag | OBSOLETE | The v4 DAG serves on-demand partial updates of a passive server. A v5 server always collects on its own schedule (decisions "Dropped — `--cached-time`"). The dependency that does matter is the processcount→processlist cascade: `tests/test_main_v5.py::test_apply_plugin_flags_disabling_processcount_disables_processlist`. |
| test_023_get_alert | COVERED | `tests/test_thresholds_v5.py::test_compute_level_high_direction`, `tests/test_plugin_cpu_v5.py::test_total_level_uses_default_thresholds` |
| test_024_split_esc | SHARED | `glances.globals.split_esc` (used by `plugins/plugin/base_v5.py`). Move out of test_core. |
| test_025_npu | PORT | The card drivers are shared, but v5 never parses `tests-data/plugins/npu/{amd,intel,rockchip}`. `test_plugin_npu_v5.py` only uses fake cards. Assert `AmdNPU/IntelNPU/RockchipNPU(npu_root_folder='./tests-data/plugins/npu/<vendor>').get_stats()[0]` equals the v4 expected dicts, in `tests/test_plugin_npu_v5.py`. |
| test_026_mpp | COVERED | `tests/test_plugin_mpp_v5.py::test_get_stats_parses_engines` (shared `RockchipMPP`, 3 engines, load/utilization). It does not assert `name`/`type`/`sessions`, which is optional to add. |
| test_093_auto_unit | SHARED | `glances.globals.auto_unit` (many v5 renderers). Move out of test_core. |
| test_094_thresholds | OBSOLETE | v4 `glances.thresholds` classes, unused by v5. Severity ordering is covered by `tests/test_thresholds_v5.py::test_compute_level_partial_thresholds_walks_severity_descending`. |
| test_095_methods | OBSOLETE | v4 plugin contract. The v5 contract is the `GlancesPluginBase` ABC, plus `tests/test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins`. |
| test_096_views | OBSOLETE | v4 views machinery. v5 has `_levels` in the payload (`tests/test_plugin_base_v5.py::test_default_levels_pipeline_writes_nested_entry`). |
| test_097_attribute | OBSOLETE | v4 `glances.attribute`, replaced by `history_v5` (`tests/test_history_v5.py`) |
| test_098_history | OBSOLETE | v4 `glances.history`, replaced by `history_v5` (`tests/test_history_v5.py`) |
| test_099_output_bars | SHARED | `glances.outputs.glances_bars.Bar` (imported by v5). Move out of test_core. |
| test_101_cpu_plugin_method | OBSOLETE | `_common_plugin_tests` exercises the v4 `GlancesPluginModel` API (`get_raw`, `get_views`, `get_stats_history`, …). v5 equivalents are in `tests/test_plugin_base_v5.py` and `tests/test_history_v5.py`. |
| test_102_load_plugin_method | OBSOLETE | idem |
| test_103_mem_plugin_method | OBSOLETE | idem |
| test_104_memswap_plugin_method | OBSOLETE | idem |
| test_105_network_plugin_method | OBSOLETE | idem |
| test_108_fs_zfs_ | GAP | `glances.plugins.fs.zfs` is not imported by any v5 module. The v4 `mem` plugin subtracts the ZFS ARC from `used` (`mem/__init__.py:180-190`), and `mem/model_v5.py` does not. The only record is a G2 "scope cut" for quicklook in `docs/architecture/tui-v4-rendering-patterns.md:585`. Nothing in the architecture-decisions or parity docs drops it. |
| test_200_views_hidden | COVERED | `tests/test_plugin_diskio_v5.py::test_hide_zero_sticky_after_threshold_burst`, `::test_hide_zero_off_by_default_never_hides` |
| test_700_mmm_feature_parent_class | OBSOLETE | mmm dropped (decisions "Dropped — min/max/mean `mmm`", 2026-09-26) |
| test_701_mmm_update_functionality | OBSOLETE | idem |
| test_702_mmm_mean_calculation | OBSOLETE | idem |
| test_703_mmm_history_limit | OBSOLETE | idem |
| test_704_mmm_handles_list_of_dicts | OBSOLETE | idem |
| test_705_mmm_ignores_non_numeric_values | OBSOLETE | idem |
| test_706_mmm_decorator_integration | OBSOLETE | idem |
| test_707_mmm_with_mem_plugin | OBSOLETE | idem |
| test_708_conf_value_convert_bool | COVERED | `tests/test_config_v5.py::test_bool_false_variants` ("False"/"0" → False), `::test_bool_true_variants` |
| test_999_the_end | OBSOLETE | `GlancesStats.end()` |

### tests/test_glances_stats.py

v4 external plugin loading (`-P/--plugins`, `plugin_dir`). In v5, `discover_plugin_classes` only walks `glances.plugins`. Decisions l.1620 says this "needs its own design" (`-P`/`--plugins`, "the v5 plugin API needs its own design"). The feature is postponed, not dropped.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_contains_plugin_model_returns_true | GAP | No external plugin directory in v5 (`main_v5.discover_plugin_classes`; parity §3 `-P` ❌, §plugin_dir ❌). |
| test_contains_plugin_model_returns_false | GAP | idem |
| test_contains_plugin_model_handles_syntax_error | GAP | idem |
| test_get_addl_plugins_returns_valid_plugins | GAP | idem |
| test_load_additional_plugins_loads_plugin | GAP | idem |

### tests/test_globals.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestExitAfter::test_preserves_result_when_queue_is_denied | SHARED | `glances.globals` stays. Note that `exit_after` is used only by the v4 `fs/__init__.py:91`, so it becomes dead code once v4 is removed. |
| TestGetIpAddress::test_default_route_address_wins_over_interface_order | SHARED | `get_ip_address` used by `ip/model_v5.py:253`, `zeroconf_v5.py:70` |
| TestGetIpAddress::test_routed_address_without_psutil_entry_returns_none_netmask | SHARED | idem |
| TestGetIpAddress::test_returns_first_matching_interface_not_last | SHARED | idem |
| TestGetIpAddress::test_loopback_probe_result_falls_back_to_interface_scan | SHARED | idem |
| TestGetIpAddress::test_skips_loopback_and_down_interfaces | SHARED | idem |
| TestGetIpAddress::test_returns_none_when_no_interface_matches | SHARED | idem |

### tests/test_json_serializer.py

`glances/outputs/glances_json_serializer.py` is v4-only, used by v4 `glances_stdout_json.py` with `include_errors=True, include_metadata=False`. v5 `--stdout-json` goes through `glances/outputs/stdout_v5.py` (`render_json` = `json.dumps(..., default=str)` over `get_export()` payloads, which are JSON-native). There, a failing plugin is silently dropped in `_exports()`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestPluginSerializationError::test_error_to_dict | GAP | v4 `--stdout-json` emits an `_errors` entry for a failing plugin. v5 logs it at debug level and drops it. No decision. |
| test_normalize_none | OBSOLETE | bytes/datetime normalisation of v4 `get_json()` bytes. v5 payloads are JSON-native, and `render_json` uses `default=str`. |
| test_normalize_bytes | OBSOLETE | idem |
| test_normalize_datetime | OBSOLETE | idem |
| test_normalize_primitives | OBSOLETE | idem |
| test_normalize_dict | OBSOLETE | idem |
| test_normalize_list | OBSOLETE | idem |
| test_normalize_nested | OBSOLETE | idem |
| test_serialize_plugin_data_none | OBSOLETE | v4 bytes-from-`get_json` contract |
| test_serialize_plugin_data_bytes_json | OBSOLETE | idem |
| test_serialize_plugin_data_bytes_invalid_json | OBSOLETE | idem |
| test_serialize_plugin_data_dict | OBSOLETE | idem |
| test_to_json_string_dict | COVERED | `tests/test_stdout_v5.py::test_json_is_one_object_keyed_by_plugin` |
| test_to_json_string_list | COVERED | `tests/test_stdout_v5.py::test_json_is_one_object_keyed_by_plugin` (the list payload of a collection is serialised as-is) |
| test_serialize_plugins_empty_list | PORT | `stdout_v5.render_json([], {}) == "{}"`, or `StdoutV5(stdout_json=...)` where no plugin matches, prints `{}` |
| test_serialize_plugins_with_data | COVERED | `tests/test_stdout_v5.py::test_output_once_writes_the_selected_format` |
| test_serialize_plugins_plugin_not_enabled | COVERED | disabled plugins are never discovered (`tests/test_main_v5.py::test_discover_plugins_skips_disabled_plugin`), so they are absent from the output (`tests/test_stdout_v5.py::test_json_is_one_object_keyed_by_plugin`) |
| test_serialize_plugins_plugin_not_found | COVERED | `tests/test_stdout_v5.py::test_json_is_one_object_keyed_by_plugin` (`"nope"` is dropped) |
| test_serialize_plugins_with_metadata | OBSOLETE | `include_metadata` is never enabled at v4 runtime |
| test_serialize_to_string_produces_valid_json | COVERED | `tests/test_stdout_v5.py::test_output_once_writes_the_selected_format` |
| test_serialize_handles_unicode | OBSOLETE | tests v4 normalisation. v5 uses stdlib `json.dumps` |
| TestSerializerEdgeCases::test_serializer_with_errors_disabled | PORT | `StdoutV5(plugins=[broken, cpu], stdout_json="mem,cpu").output_once()` still writes valid JSON `{"cpu": …}`. Only the plain mode is tested today (`test_a_failing_plugin_does_not_end_the_stream`). |
| test_serializer_with_errors_enabled | GAP | `_errors` reporting (see test_error_to_dict) |
| test_multiple_plugins_one_fails | GAP | the `_errors` part. The "good plugin kept" part is folded into the PORT above. |
| test_empty_bytes_input | OBSOLETE | v4 bytes contract |
| test_all_plugins_fail_still_produces_valid_json | GAP | the `_errors` part. Port the "valid `{}` when all fail" half along with the PORT above. |
| test_empty_plugins_produces_valid_json | PORT | same PORT as test_serialize_plugins_empty_list |
| test_output_structure_consistency | OBSOLETE | `_metadata` is never enabled at v4 runtime |

### tests/test_actions_sanitize.py

v4 `GlancesActions` and `_sanitize_mustache_dict` are not used by v5. v5 `ShellAction` (`glances/actions_v5/shell/__init__.py`) does no operator stripping. It relies on split-then-render inside the shared `secure_popen(render=...)`. The decisions table records this for GHSA-73wf-9vmv-5pv9 and GHSA-qcpp-8x79-hhp3 ("v5 does not use v4's operator-stripping sanitizer at all").

**Doc drift:** those decision rows still describe a `shlex.quote` / `create_subprocess_shell` / `allow_shell()` implementation. They also cite `test_nested_list_value_reaches_shell_as_single_token`, which no longer exists; the current test is `test_nested_list_value_reaches_one_argument`.

The dedup and repeat logic moved from `GlancesActions` to `GlancesAlerts` (`alerts_v5.py:433-442`).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestSanitizeMustacheDict::test_none_returns_none | OBSOLETE | v4-only sanitizer. v5 makes values inert structurally (decisions GHSA-73wf / GHSA-qcpp rows); see `tests/test_action_shell_v5.py`. |
| …::test_empty_dict_returns_empty | OBSOLETE | idem |
| …::test_strips_pipe | OBSOLETE | idem |
| …::test_strips_double_ampersand | OBSOLETE | idem |
| …::test_strips_redirect | OBSOLETE | idem |
| …::test_strips_append_redirect | OBSOLETE | idem |
| …::test_strips_multiple_operators | OBSOLETE | idem |
| …::test_preserves_int_values | OBSOLETE | idem |
| …::test_preserves_float_values | OBSOLETE | idem |
| …::test_preserves_none_values | OBSOLETE | idem |
| …::test_preserves_bool_values | OBSOLETE | idem |
| …::test_preserves_list_of_numbers | OBSOLETE | idem |
| …::test_strips_operators_in_nested_list | OBSOLETE | idem. The v5 equivalent is `tests/test_action_shell_v5.py::test_nested_list_value_reaches_one_argument`. |
| …::test_strips_operators_in_nested_dict | OBSOLETE | idem |
| …::test_strips_operators_in_deeply_nested | OBSOLETE | idem |
| …::test_preserves_tuple_type | OBSOLETE | idem |
| …::test_sanitize_value_passthrough_non_string | OBSOLETE | idem |
| …::test_clean_string_unchanged | OBSOLETE | idem |
| …::test_does_not_mutate_original | OBSOLETE | idem |
| …::test_returns_new_dict | OBSOLETE | idem |
| TestCommandInjectionPrevention::test_pipe_injection_in_process_name | OBSOLETE | asserts sanitizer output. Injection prevention in v5: `tests/test_action_shell_v5.py::test_shell_metacharacters_cannot_start_a_command`, `::test_value_cannot_execute_a_second_command` |
| …::test_chain_injection_in_container_name | OBSOLETE | idem. `tests/test_action_shell_v5.py::test_nested_list_value_reaches_one_argument` |
| …::test_redirect_injection_in_mount_point | OBSOLETE | idem. Shared `TestSecurePopenRender::test_operators_in_the_value_are_never_interpreted` |
| …::test_append_redirect_injection | OBSOLETE | idem |
| …::test_lone_ampersand_is_stripped | OBSOLETE | idem. `tests/test_action_shell_v5.py::test_adjacent_unescaped_variables_cannot_reconstruct_operator` |
| …::test_cross_field_ampersand_reconstruction_blocked | OBSOLETE | idem (same v5 test) |
| TestSecurePopen::test_simple_echo | SHARED | `glances.secure`, called from `actions_v5/shell/__init__.py` and `amps/default`. Relocate out of this file. |
| TestSecurePopen::test_chained_commands | SHARED | idem |
| TestSecurePopen::test_pipe | SHARED | idem |
| TestSecurePopen::test_redirect_to_file | SHARED | idem |
| TestActionsRunIntegration::test_run_with_safe_values | COVERED | `tests/test_action_shell_v5.py::test_renders_simple_template_and_executes` |
| …::test_run_sanitizes_pipe_in_mustache | COVERED | `tests/test_action_shell_v5.py::test_shell_metacharacters_cannot_start_a_command` (one process, value in one argv slot; v5 keeps the text verbatim by design) |
| …::test_run_sanitizes_chain_in_mustache | COVERED | `tests/test_action_shell_v5.py::test_nested_list_value_reaches_one_argument` (`&&` in the value, one process, 2 argv) |
| …::test_run_sanitizes_redirect_in_mustache | COVERED | `tests/test_action_shell_v5.py::test_value_cannot_execute_a_second_command` plus shared `TestSecurePopenRender::test_operators_in_the_value_are_never_interpreted`, reached through the `render=` call site in `ShellAction.execute` |
| …::test_run_preserves_template_operators | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_pipes` |
| …::test_run_preserves_template_redirect | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_interprets_operators` |
| …::test_run_preserves_template_chain | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_pipes` (template operators honoured) plus shared `TestSecurePopen::test_chained_commands`. Optional: add an `&&` variant. |
| …::test_run_sanitizes_cmdline_section | COVERED | `tests/test_action_shell_v5.py::test_section_within_one_argument_is_rendered`, `::test_nested_list_value_reaches_one_argument` |
| …::test_run_blocks_cross_field_ampersand_chain | COVERED | `tests/test_action_shell_v5.py::test_adjacent_unescaped_variables_cannot_reconstruct_operator` |
| …::test_run_does_not_execute_when_already_triggered | PORT | No v5 test runs two cycles at the same level with a non-repeat `warning_action` and asserts a single call. `test_non_repeat_action_fires_on_entry` runs one cycle only. Add it to `tests/test_alerts_v5.py` against `GlancesAlerts.ingest_plugin` (`alerts_v5.py:433-442`): 2× warning cycles → `[c["repeat"] for c in action.calls] == [False]`. |
| …::test_run_repeats_when_repeat_true | COVERED | `tests/test_alerts_v5.py::test_repeat_action_fires_every_cycle_while_committed_non_ok` |
| TestActionsDisableConfigExec::test_allow_operators_true_when_no_args | COVERED | `tests/test_action_shell_v5.py::test_default_config_exec_is_allowed` |
| …::test_allow_operators_true_when_flag_absent | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_interprets_operators` (config without the key) |
| …::test_allow_operators_false_when_disabled | COVERED | `tests/test_action_shell_v5.py::test_flag_disables_operators` |
| …::test_allow_operators_true_when_enabled | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_interprets_operators`, `::test_enabled_still_pipes` |
| …::test_run_passes_allow_operators_false_when_disabled | COVERED | `tests/test_action_shell_v5.py::test_disabled_runs_as_a_single_process`, `::test_disabled_makes_operators_literal` |
| …::test_run_passes_allow_operators_true_by_default | COVERED | `tests/test_action_shell_v5.py::test_enabled_still_pipes` |
| …::test_run_disabled_does_not_write_redirect_file | COVERED | `tests/test_action_shell_v5.py::test_disabled_makes_operators_literal` |
| TestActionsArgumentInjection::test_poc_single_quoted_field_stays_one_argument | COVERED | `tests/test_action_shell_v5.py::test_poc_single_quoted_field_stays_one_argument` |
| …::test_unquoted_field_with_spaces_stays_one_argument | COVERED | `tests/test_action_shell_v5.py::test_unquoted_field_with_spaces_stays_one_argument` |
| …::test_double_quoted_field_stays_one_argument | PORT | v5 has the double-quoted template only in the e2e `test_value_cannot_execute_a_second_command` (asserts that no second command runs, not the argv shape). Add `'argv_logger.py "{{mnt_point}}" {{percent}}'` → `[['argv_logger.py', _POC_VALUE, '92']]` against `ShellAction.execute` in `tests/test_action_shell_v5.py`. |
| …::test_triple_mustache_stays_one_argument | COVERED | `tests/test_action_shell_v5.py::test_triple_mustache_stays_one_argument` |
| …::test_ampersand_mustache_stays_one_argument | PORT | no `{{&var}}` case in v5. Add `'argv_logger.py {{&mnt_point}} {{percent}}'` → one argv slot, against `ShellAction.execute`. |
| …::test_empty_value_yields_an_empty_argument | COVERED | `tests/test_action_shell_v5.py::test_empty_value_yields_an_empty_argument` |
| …::test_protection_holds_with_disable_config_exec | COVERED | `tests/test_action_shell_v5.py::test_protection_holds_with_disable_config_exec` |
| …::test_section_within_one_argument_is_rendered | COVERED | `tests/test_action_shell_v5.py::test_section_within_one_argument_is_rendered` |
| …::test_section_spanning_two_arguments_is_refused | COVERED | `tests/test_action_shell_v5.py::test_template_render_error_is_logged_and_skips_exec` |
| …::test_templated_redirect_target_is_expanded | PORT | no v5 test has a Mustache field in the redirect target. Add `ShellAction().execute('fs','critical',{'name':'disk1'}, 'echo -n ALERT > <tmp>/gl_{{name}}.alert')` → file `gl_disk1.alert` exists. |
| TestSecurePopenRender::test_operators_in_the_value_are_never_interpreted | SHARED | `glances.secure.secure_popen(render=...)`, exactly the v5 call path (`actions_v5/shell/__init__.py`, `render=partial(chevron.render, data=context)`). Relocate. |
| …::test_quotes_in_the_value_cannot_break_out | SHARED | idem |
| …::test_whitespace_in_the_value_cannot_split | SHARED | idem |
| …::test_render_is_not_applied_when_omitted | SHARED | idem (AMP/virsh/multipass callers, all shared) |

### tests/test_amp_secure_popen.py

Shared code path. `AmpsListV5` imports `glances.amps.<name>` or falls back to `glances.amps.default` (`amps_list_v5.py:_DEFAULT_MODULE`). It builds `module.Amp(name=name, args=SimpleNamespace(disable_config_exec=…))`, the same contract the test builds with `Namespace`. `Amp.update()` → `secure_popen(..., allow_operators=self.allow_operators(), timeout=self.timeout())` is unchanged v4 code.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestSecurePopenNoOperators::test_redirect_does_not_write_file | SHARED | `glances.secure` |
| …::test_chaining_is_not_interpreted | SHARED | idem |
| …::test_pipe_is_not_interpreted | SHARED | idem |
| TestAmpRedirectMitigation::test_disable_config_exec_blocks_file_write | SHARED | `glances.amps.default.Amp`, loaded by `amps_list_v5.py`. Shim covered by `tests/test_amps_list_v5.py::test_disable_config_exec_reaches_the_amp`. |
| …::test_default_behaviour_unchanged | SHARED | idem |
| test_timeout_none_is_the_default_and_changes_nothing | SHARED | `glances.secure` |
| test_timeout_not_reached_returns_the_output | SHARED | idem |
| test_timeout_kills_a_hanging_command | SHARED | idem |
| test_timeout_applies_without_operators | SHARED | idem |
| test_amp_timeout_accessor_defaults_to_none | SHARED | `glances.amps.amp.GlancesAmp.timeout` |
| test_amp_timeout_accessor_reads_the_config_key | SHARED | idem |
| test_amp_timeout_accessor_coerces_string_to_float | SHARED | idem |
| test_amp_timeout_accessor_rejects_non_numeric_value | SHARED | idem |
| test_timeout_bounds_a_pipeline_whose_upstream_stage_hangs | SHARED | `glances.secure` |
| test_timeout_kills_and_reaps_a_multi_process_pipeline | SHARED | idem |

### tests/test_processes_cache.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_remove_non_running_procs_keeps_running_pids | SHARED | `glances.processes.GlancesProcesses` (v5 engine) |
| test_remove_non_running_procs_evicts_everything_when_no_proc_runs | SHARED | idem |
| test_remove_non_running_procs_is_noop_when_all_running | SHARED | idem |
| test_remove_non_running_procs_ignores_running_pids_absent_from_cache | SHARED | idem |
| test_remove_non_running_procs_evicts_io_old_of_gone_pids | SHARED | idem |
| test_io_old_stays_bounded_across_cycles_of_short_lived_pids | SHARED | idem |

### tests/test_processes_extended.py

All tests use only `glances.processes.GlancesProcesses`. `extended_pid` is the v5 2.X-b3 pin, driven by `glances_curses_v5`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_no_pid_is_selected_by_default | SHARED | `glances.processes` |
| test_the_pinned_pid_is_selected | SHARED | idem |
| test_a_process_without_a_pid_is_never_selected | SHARED | idem |
| test_position_selection_is_inert_without_args | SHARED | idem |
| test_the_update_loop_actually_uses_the_pinned_pid | SHARED | idem |
| test_no_pin_means_no_extended_grab | SHARED | idem |
| test_a_pinned_process_that_exits_is_forgotten | SHARED | idem |
| test_a_pinned_process_that_is_still_running_is_kept | SHARED | idem |
| test_a_failed_swap_read_reports_no_figure_rather_than_raising | SHARED | idem |
| test_a_readable_process_still_reports_its_swap | SHARED | idem |
| test_access_denied_reports_no_figure_too | SHARED | idem |
| test_min_max_mean_accumulate_while_pinned | SHARED | idem |
| test_a_new_pin_starts_from_fresh_min_max_mean | SHARED | idem |
| test_the_pinned_process_carries_its_command_line | SHARED | idem |

### tests/test_processes_nice.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_an_applied_renice_reports_success (×2 params) | SHARED | `GlancesProcesses.nice_increase/decrease`, whose return value the v5 TUI uses (decisions l.1412) |
| test_a_refused_renice_reports_failure_instead_of_raising (×2) | SHARED | idem |
| test_a_vanished_process_still_raises (×2) | SHARED | idem |

### tests/test_program_aggregation.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_aggregation_is_reused_while_the_list_is_unchanged | SHARED | `GlancesProcesses.get_list(as_programs=True)`, called by `programlist/model_v5.py:178` |
| test_aggregation_is_rebuilt_when_the_list_is_replaced | SHARED | idem |
| test_aggregation_follows_a_re_sort | SHARED | idem |
| test_aggregation_content | SHARED | idem |
| test_aggregation_follows_an_in_place_sort | SHARED | idem |

### tests/test_program_io_counters.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_io_counters_keep_their_five_slots | SHARED | `glances.programs.processes_to_programs` (imported by `glances/processes.py:24`) |
| test_io_counters_are_summed_slot_by_slot | SHARED | idem |
| test_io_tag_is_a_flag_not_a_total | SHARED | idem |
| test_io_tag_is_set_when_any_process_reports_io | SHARED | idem |
| test_io_tag_stays_unset_when_no_process_reports_io | SHARED | idem |
| test_a_process_without_io_counters_is_skipped_not_fatal | SHARED | idem |
| test_a_first_process_without_io_counters_still_yields_a_list | SHARED | idem |
| test_the_program_does_not_borrow_the_process_list | SHARED | idem |
| test_repeated_aggregation_does_not_grow_the_counters | SHARED | idem |

### tests/test_programs_aggregation.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_zero_totals_keep_their_field | SHARED | `glances.programs.sum_field_dict` |
| test_missing_field_is_added | SHARED | idem |
| test_none_operands_are_tolerated | SHARED | idem |
| test_aggregated_program_keeps_every_cpu_times_field | SHARED | `glances.programs.processes_to_programs` |
| test_aggregated_program_keeps_every_memory_info_field | SHARED | idem |

### tests/test_sort_missing_values.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_sort_cpu_times_reads_a_missing_value_as_zero | SHARED | `glances.processes._sort_cpu_times` (`sort_stats` is imported by v5) |
| test_sort_io_counters_reads_a_missing_value_as_zero | SHARED | `glances.processes._sort_io_counters` |
| test_one_row_without_cpu_times_does_not_reorder_the_others | SHARED | `glances.processes.sort_stats` |
| test_one_row_without_io_counters_does_not_reorder_the_others | SHARED | idem |

---

### Summary (test functions; parametrised tests counted once)

| File | SHARED | COVERED | PORT | OBSOLETE | GAP | Total |
|---|---|---|---|---|---|---|
| test_core.py | 7 | 21 | 2 | 22 | 3 | 55 |
| test_glances_stats.py | 0 | 0 | 0 | 0 | 5 | 5 |
| test_globals.py | 7 | 0 | 0 | 0 | 0 | 7 |
| test_json_serializer.py | 0 | 6 | 3 | 15 | 4 | 28 |
| test_actions_sanitize.py | 8 | 25 | 4 | 26 | 0 | 63 |
| test_amp_secure_popen.py | 15 | 0 | 0 | 0 | 0 | 15 |
| test_processes_cache.py | 6 | 0 | 0 | 0 | 0 | 6 |
| test_processes_extended.py | 14 | 0 | 0 | 0 | 0 | 14 |
| test_processes_nice.py | 3 | 0 | 0 | 0 | 0 | 3 |
| test_program_aggregation.py | 5 | 0 | 0 | 0 | 0 | 5 |
| test_program_io_counters.py | 9 | 0 | 0 | 0 | 0 | 9 |
| test_programs_aggregation.py | 5 | 0 | 0 | 0 | 0 | 5 |
| test_sort_missing_values.py | 4 | 0 | 0 | 0 | 0 | 4 |
| **Total** | **83** | **52** | **9** | **63** | **12** | **219** |

## v4 → v5 test migration audit — group 4 (REST / API / MCP / browser / TUI / WebUI / CLI / stdout / perf)

Branch `develop-v5`, read-only analysis. Sources: `docs/architecture/glances-v5-architecture-decisions.md`
(§1.1 XML-RPC removed, §1.3 StatsStore, §3.6 views rejected, §4.6 routes + "Deferred for follow-up",
§8 CVE table, §10 parity backlog and "Dropped" notes), `docs/architecture/glances-v5-v4-parity-inventory.md`,
and the v5 code/tests. Every COVERED citation was read in the v5 test file. Behaviours marked PORT were
checked to exist in v5 code (several by running a throw-away probe against `build_app`, `CsvRenderer`).

Notes that apply throughout:

- **Harness steps** (`test_000_start_server`, `test_999_stop_server`, …) spawn `python -m glances …`, i.e.
  the **v4** entry point (`glances/__main__.py` → `glances.main()`); v5 is `glances-v5 = glances.main_v5:main`.
  They assert nothing but `Popen` returning. v5 tests use in-process `TestClient(build_app(...))` instead, so
  these are OBSOLETE as harness. The same applies to `tests/conftest.py::glances_webserver` / `glances_stats`
  / `glances_stats_no_history`, which build v4 objects.
- Stdout modes **are ported**: `--stdout`, `--stdout-json`, `--stdout-csv` live in `glances/outputs/stdout_v5.py`
  (§10, "2026-09-25 — 32 v4 CLI options shipped"; the parity inventory still says ❌ — it is stale on this point).
- `-w/--webserver` is a v5 alias of `-s` (§10, same note), so `-w` in a v4 test is not by itself a reason for OBSOLETE.
- `glances/outputs/glances_mcp.py` is shared, but every v4 MCP test drives it through the v4 server
  (`GlancesRestfulApi` + v4 `GlancesStats`), so none of them is SHARED.
- `glances/outdated.py` is not imported by any `*_v5.py` file; §8 (CVE-2026-46607) says the update check is
  to be "carried forward (version-check port)" — not dropped — hence GAP, not OBSOLETE.

---

### tests/test_restful.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_000_start_server | OBSOLETE | Harness (spawns v4 `-w --browser`); v5 tests build the app in-process. |
| test_001_all | COVERED | `tests/test_routes_v5.py::test_all_returns_store_dict`. The "second call is cached/faster" half is OBSOLETE: v5 serves the pre-computed StatsStore (§1.3), there is no request cache. |
| test_002_pluginslist | COVERED | `tests/test_routes_v5.py::test_pluginslist_sorted` (list); real `cpu` discovery: `tests/test_main_v5.py::test_discover_plugins_finds_concrete_v5_plugins`. |
| test_003_plugins | PORT | No v5 test hits every **real** plugin through REST (routes tests use fake plugins). Port: `assemble(build_parser().parse_args(["-s"]), config)` (`glances/main_v5.py`), run one `plugin.update()` per registered plugin, then for each name in `/api/5/pluginslist` GET `/api/5/<plugin>` → 200 and a dict (scalar) or the `{"data": [...]}` envelope (collection), each item a dict. |
| test_004_items | GAP | `/api/5/<plugin>/<field>` does not exist; §4.6 lists it under "Deferred for follow-up" (not dropped). |
| test_005_values | GAP | `/api/5/<plugin>/<pk>/value/<v>` (collection item lookup) absent; §4.6 "Deferred for follow-up". |
| test_006_all_limits | COVERED | `tests/test_routes_v5.py::test_all_limits_is_not_captured_by_the_dynamic_route`, `::test_all_limits_omits_plugins_without_thresholds`. |
| test_007_all_views | OBSOLETE | Views rejected by design (§3.6, `update_views()` stripped §3.1); per-field levels ship as `_levels` in the payload (`test_routes_v5.py::test_plugin_payload_scalar`). |
| test_008_plugins_limits | COVERED | `tests/test_routes_v5.py::test_plugin_limits_returns_thresholds`, `::test_plugin_limits_empty_dict_when_no_watched_field`. |
| test_009_plugins_views | OBSOLETE | §3.6 (no `/views`). |
| test_010_history | COVERED | `tests/test_routes_v5.py::test_history_scalar_shape`, `::test_history_nb_field_and_an_item_with_a_slash`, `::test_history_collection_nests_by_field_then_raw_item`. Shape/paths changed by decision (§4.6 history row: `?nb=&field=&item=`, columnar). |
| test_011_issue1401 | GAP | `/api/5/network/interface_name` (field accessor) absent; §4.6 deferred. |
| test_012_status | COVERED | `tests/test_webserver_v5.py::test_status_endpoint` (`glances_version == __version__`; `version` is now the API version). |
| test_013_top | GAP | `/api/5/<plugin>/top/<n>` absent; not listed in any decision. |
| test_014_config | GAP | `/api/5/config` itself is COVERED (`test_routes_v5.py::test_config_open_when_no_auth`), but `/config/<section>/<key>` (asserted `== "2"`) does not exist and no decision drops it. |
| test_015_all_gzip | GAP | v5 wires no `GZipMiddleware` (`webserver_v5.build_app`; v4 `glances_restful_api.py:305`). No decision mentions compression. |
| test_016_fields_description | COVERED | Replaced by `/api/5/<plugin>/info` (§4.6): `tests/test_routes_v5.py::test_plugin_info_returns_schema` asserts `unit`. Per-field `/description` and `/unit` paths are gone with the field accessor (see test_004). |
| test_017_item_key | GAP | `/api/5/<plugin>/<field>/<pk>` absent; §4.6 deferred. |
| test_050_start_cors_server | OBSOLETE | Harness for test_051. |
| test_051_cors_credentials_disabled_for_wildcard_in_list | COVERED | `tests/test_webserver_v5.py::test_cors_multi_origin_allowlist_with_wildcard_downgrades` (+ `::test_cors_wildcard_with_credentials_downgrades` for `ACAO: *`, no credentials). |
| test_100_browser | COVERED | `tests/test_servers_list_v5.py::test_serverslist_never_carries_a_credential` (200, list of dicts). |
| test_101_static_files_are_revalidated | COVERED | `tests/test_webserver_v5.py::test_the_v5_bundle_is_revalidated_by_the_browser`. |
| test_999_stop_server | OBSOLETE | Harness. |

### tests/test_api.py (v4 Python API `glances.api`)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_glances_api_version | COVERED | `tests/test_api_v5.py::test_version_is_the_major`. |
| test_glances_api_plugins | PORT | Every v5 API test restricts `plugins=`. Port: `with glances.api_v5.GlancesAPI() as gl:` (default = all enabled plugins) → `gl.plugins()` non-empty and contains `cpu`, `network`, `processcount`, `processlist`. |
| test_glances_api_plugin_cpu | COVERED | Scalar view semantics (`keys()`, `[]`, `.get`): `tests/test_api_v5.py::test_a_scalar_view_is_keyed_by_field`, `::test_a_view_is_a_read_only_mapping_snapshot` (on `mem`; cpu values typed in `test_plugin_cpu_v5.py`). |
| test_glances_api_plugin_network | COVERED | `tests/test_api_v5.py::test_the_first_read_has_rates` (iterates `gl.network.values()` dict items). |
| test_glances_api_plugin_process | COVERED | `tests/test_api_v5.py::test_a_collection_view_is_keyed_by_primary_key` (int pid keys → dict), `::test_processlist_updates_processcount_first`. |
| test_glances_api_limits | COVERED | `tests/test_api_v5.py::test_a_view_matches_what_rest_serves` (`view.limits == plugin.get_limits()`), `::test_config_path_layers_over_the_defaults`. |

### tests/test_api_secure.py (CVE-2026-68520 — `/config`, `/args` redaction)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_url_embedded_credentials_are_redacted | COVERED | `tests/test_config_v5.py::test_redacts_credentials_embedded_in_url_value`. |
| test_url_without_credentials_is_untouched | COVERED | `tests/test_config_v5.py::test_preserves_url_without_credentials`, `::test_preserves_non_secret`. |
| test_every_url_of_a_multi_url_value_is_redacted | COVERED | Same value-level rule per key: `tests/test_config_v5.py::test_redacts_credentials_embedded_in_url_value` (the v4 case is two keys, `web_1_url`/`web_2_url`, each one URL). |
| test_login_names_are_redacted | COVERED | `tests/test_config_v5.py::test_redacts_username_and_login_keys`, `::test_redacts_bare_user_key`. |
| test_passwords_are_still_redacted | COVERED | `tests/test_config_v5.py::test_redacts_passwords`. |
| test_passwords_section_is_still_blocked | COVERED | `tests/test_phase3_cve_v5.py::test_config_route_never_serves_the_passwords_section`. |
| test_cpu_user_thresholds_are_not_redacted | COVERED | `tests/test_config_v5.py::test_preserves_user_prefixed_thresholds`. |
| test_args_login_is_redacted | PORT | No v5 test asserts the `username` arg is redacted (`-u` is accepted with `-s --browser`). Port in `tests/test_routes_v5.py`: `build_app(..., args=Namespace(username="alice"))` → `GET /api/5/args` → `payload["username"] == "***"` (`routes_v5._redact_args`). |
| test_args_url_embedded_credentials_are_redacted | COVERED | `tests/test_routes_v5.py::test_args_redacts_credentials_embedded_in_a_value`. |
| test_args_hardcoded_sensitive_keys_are_still_redacted | PORT | `config_path` (v4 `conf_file`) COVERED by `test_routes_v5.py::test_args_redacts_the_config_file_path`; SNMP keys OBSOLETE (SNMP dropped, §5/§10). Remaining: assert `username` → `"***"` (same port as test_args_login_is_redacted; one v5 test closes both). |
| test_args_non_string_values_keep_their_type | COVERED | `tests/test_routes_v5.py::test_args_returns_the_argument_namespace` (`port` int, `server` bool). Deliberate divergence: v5 over-redacts booleans whose key contains `password` (`set_password` → `"***"`, asserted in `::test_args_matches_the_real_v5_argument_set`). |
| test_args_authenticated_view_only_redacts_the_password | OBSOLETE | v5 redacts `/args` and `/config` **unconditionally** (§4.6 `/config` row; `routes_v5._redact_args` docstring "Redaction is UNCONDITIONAL"). Stricter than v4; flag for the §4.8 audit since CLAUDE.md still describes the v4 conditional rule. |

### tests/test_xmlrpc.py

All XML-RPC machinery is removed (§1.1). Security properties that §8 says are now carried by the REST stack
(CVE-2026-46608 "v5 CORS reflects only exact-match origins", CVE-2026-46611 "covered by TrustedHostMiddleware")
are mapped to the REST layer when no v5 test asserts them.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_000_start_server | OBSOLETE | §1.1 (XML-RPC server removed); harness. |
| test_001_default_accepts_any_host | OBSOLETE | §1.1. |
| test_010_start_secure_server | OBSOLETE | §1.1; harness. |
| test_011_secure_rejects_spoofed_host | COVERED | REST equivalent: `tests/test_webserver_v5.py::test_trusted_host_allowlist_enforced` (400). |
| test_012_secure_accepts_listed_host | COVERED | `tests/test_webserver_v5.py::test_trusted_host_allowlist_enforced` (200). |
| test_013_secure_wildcard_match | PORT | Not asserted in v5. Port to `webserver_v5._wire_trusted_hosts`: `webui_allowed_hosts=*.glances.test` → `Host: node1.glances.test` 200 (verified to work). |
| test_014_secure_wildcard_no_bare_match | PORT | Same target: `Host: glances.test` → 400 (verified). |
| test_015_secure_strips_port | PORT | Same target: `webui_allowed_hosts=127.0.0.1`, `Host: 127.0.0.1:61208` → 200 (verified). |
| test_016_secure_missing_host_rejected | PORT | Same target: HTTP/1.0 request without `Host` → 400 when an allowlist is set (raw-socket or ASGI scope without host header). |
| test_020_default_cors_wildcard | OBSOLETE | §1.1; and the v5 default is deliberately "no CORS" (§4.3; parity inventory `cors_origins` row), asserted by `test_webserver_v5.py::test_cors_absent_by_default`. |
| test_030_start_cors_server | OBSOLETE | §1.1; harness. |
| test_031_cors_reflects_first_allowed_origin | PORT | v5 only tests a one-origin allowlist. Port to `webserver_v5._wire_cors`: `cors_origins=https://a,https://b` → Origin `https://a` echoed, `Vary` contains `Origin` (verified). Backs §8 CVE-2026-46608 "resolved by architecture". |
| test_032_cors_reflects_second_allowed_origin | PORT | Same test: Origin `https://b` echoed too, never `*`. |
| test_033_cors_foreign_origin_no_header | COVERED | `tests/test_webserver_v5.py::test_cors_allowlist_enforced` (evil origin → no ACAO). |
| test_034_cors_no_origin_no_header | PORT | With an allowlist wired, a request without `Origin` gets no `Access-Control-Allow-Origin` (verified); not asserted in v5. |
| test_999_stop_server | OBSOLETE | §1.1; harness. |

### tests/test_mcp.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestGlancesMcp::test_000_start_server | OBSOLETE | Harness (v4 server). |
| TestGlancesMcp::test_001_sse_endpoint_reachable | PORT | v5 only checks the mount and the 401 (`test_webserver_v5.py::test_attach_mcp_mounts_when_gate_on`, `::test_a_custom_mcp_path_stays_behind_auth`). Port: `attach_mcp(app, enable_mcp=true)` then `GET /mcp/sse` (stream) → 200, `content-type` contains `text/event-stream`. |
| TestGlancesMcp::test_010_list_resources | PORT | No v5 test lists MCP resources. Port: `GlancesMcpServer(stats=McpStatsAdapter(plugins=[...]), args=None, config=config)` (`glances/outputs/mcp_adapter_v5.py`) → `list_resources()` contains `glances://plugins`, `glances://stats`, `glances://limits`. |
| TestGlancesMcp::test_011_list_resource_templates | PORT | Same harness → templates contain `glances://stats/{plugin}`, `glances://stats/{plugin}/history`, `glances://limits/{plugin}`. |
| TestGlancesMcp::test_012_read_resource_plugins | COVERED | Data asserted at the adapter: `tests/test_mcp_adapter_v5.py::test_get_plugins_list_returns_registered_names`. |
| TestGlancesMcp::test_013_read_resource_all_stats | COVERED | `tests/test_mcp_adapter_v5.py::test_get_all_as_dict_returns_every_plugin_payload`. |
| TestGlancesMcp::test_014_read_resource_plugin_cpu | COVERED | `tests/test_mcp_adapter_v5.py::test_plugin_view_get_raw_returns_store_value` (cpu stub). |
| TestGlancesMcp::test_015_read_resource_limits_cpu | COVERED | `tests/test_mcp_adapter_v5.py::test_plugin_view_get_limits_aggregates_default_thresholds`, `::test_get_plugin_limits_reflects_a_config_override`. |
| TestGlancesMcp::test_020_list_prompts | PORT | Port with the same `GlancesMcpServer`+`McpStatsAdapter` harness: `list_prompts()` names include `system_health_summary`, `alert_analysis`, `top_processes_report`, `storage_health`. |
| TestGlancesMcp::test_021_get_prompt_system_health | PORT | `get_prompt("system_health_summary")` text contains `Glances` and `cpu` over v5 payloads. |
| TestGlancesMcp::test_022_get_prompt_alert_analysis_with_arg | PORT | `get_prompt("alert_analysis", {"level": "critical"})` over the v5 alert view (`McpStatsAdapter` synthetic `alert`). |
| TestGlancesMcp::test_023_get_prompt_top_processes_with_arg | COVERED | `tests/test_mcp_adapter_v5.py::test_top_processes_prompt_accepts_the_collection_envelope`. |
| TestGlancesMcp::test_999_stop_server | OBSOLETE | Harness. |
| TestGlancesMcpAuthMiddleware::test_auth_non_mcp_path_passes_through | OBSOLETE | v4 `GlancesMcpAuthMiddleware` is not used by v5: `/mcp` sits behind the single global auth middleware (`webserver_v5._wire_auth`, §4.3, §11.6). |
| …::test_auth_mcp_subpath_is_intercepted | COVERED | `tests/test_webserver_v5.py::test_a_custom_mcp_path_stays_behind_auth` (`/…/mcp/sse` → 401). |
| …::test_auth_no_password_mcp_path_open | COVERED | `tests/test_webserver_v5.py::test_no_auth_when_password_absent` (middleware is path-agnostic, not wired without a password). |
| …::test_auth_correct_basic_credentials_pass | COVERED | `tests/test_webserver_v5.py::test_basic_auth_accepts_correct_credentials`. |
| …::test_auth_wrong_password_rejected | COVERED | `tests/test_webserver_v5.py::test_basic_auth_rejects_wrong_password`. |
| …::test_auth_wrong_username_rejected | COVERED | `tests/test_webserver_v5.py::test_basic_auth_rejects_wrong_username`. |
| …::test_auth_no_credentials_rejected | COVERED | `tests/test_webserver_v5.py::test_basic_auth_rejects_missing_authorization`. |
| …::test_auth_valid_jwt_passes | COVERED | `tests/test_webserver_v5.py::test_bearer_auth_accepts_valid_jwt`. |
| …::test_auth_invalid_jwt_rejected | COVERED | `tests/test_webserver_v5.py::test_bearer_auth_rejects_invalid_jwt`. |
| …::test_auth_options_preflight_bypasses_auth | PORT | v5 relies on CORSMiddleware sitting outside Auth (§4.3) to answer preflights; verified (`OPTIONS` + `Origin` + `Access-Control-Request-Method` → 200 with password set) but not asserted. Port to `tests/test_webserver_v5.py` against `build_app` (password + `cors_origins`), on `/api/5/…` and on the MCP mount. |
| …::test_auth_lifespan_scope_bypasses_auth | OBSOLETE | ASGI internals of the v4 middleware; v5 uses `@app.middleware("http")`, which never sees lifespan. |
| …::test_auth_401_response_has_www_authenticate_header | COVERED | `tests/test_webserver_v5.py::test_basic_auth_rejects_wrong_password` (`WWW-Authenticate: Basic`), `::test_bearer_auth_rejects_invalid_jwt`. |

### tests/test_browser_restful.py (`/serverslist`, CVE-2026-32633)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestServersListEndpoint::test_serverslist_returns_200 | COVERED | `tests/test_servers_list_v5.py::test_serverslist_never_carries_a_credential`. |
| …::test_serverslist_returns_list | COVERED | Same test (`[item] = response.json()`). |
| …::test_serverslist_has_servers | COVERED | Same test (one configured static server → one entry); `::test_the_static_list_reads_v4s_layout`. |
| …::test_serverslist_server_has_required_fields | COVERED | Same test: `set(item) == {name, alias, port, status, source, columns}` (field set redesigned in P3; `key/ip/protocol/type` gone). |
| …::test_serverslist_server_types | COVERED | `source` replaces `type`: `tests/test_zeroconf_v5.py::test_discovery_lists_the_v5_announcements_only` (`"zeroconf"`), static default in `test_servers_list_v5.py::test_a_non_static_server_gets_no_configured_password`. |
| …::test_serverslist_server_protocols | OBSOLETE | §1.1 (no `rpc`; `protocol` ignored with a warning — `test_servers_list_v5.py::test_a_real_config_file_with_passwords_and_protocols`). |
| TestServersListCredentialSanitization::test_no_password_field_in_response | COVERED | `tests/test_servers_list_v5.py::test_serverslist_never_carries_a_credential`. |
| …::test_no_uri_field_in_response | COVERED | Same test. |
| …::test_no_credential_in_any_field | COVERED | Same test (scans the JSON for the password, `uri`, `Bearer`, …). |
| TestSanitizeServer::test_strips_password | OBSOLETE | v4 `GlancesRestfulApi._sanitize_server` replaced by a whitelist (`ServerEntry.as_dict`, entries hold no credential); property covered by `test_serverslist_never_carries_a_credential`. |
| TestSanitizeServer::test_strips_uri | OBSOLETE | Same. |
| TestSanitizeServer::test_preserves_other_fields | OBSOLETE | Same (field set asserted by the v5 test). |
| TestSanitizeServer::test_does_not_mutate_original | OBSOLETE | Same (no sanitiser to mutate). |
| TestSanitizeServer::test_handles_missing_fields | OBSOLETE | Same. |
| TestServersListStability::test_repeated_calls_consistent | PORT | v5 test does one `poll_round()`. Port: several `poller.poll_round()` + `GET /api/5/serverslist` give the same entry count (`glances/servers_list_v5.py` + `routes_v5._servers_list`). |
| TestServersListStability::test_repeated_calls_never_leak_credentials | PORT | Repeat the leak scan of `test_serverslist_never_carries_a_credential` after a second round with a typed password (`poller.set_password`) — a credential added after the first round is the case v5 does not assert. |

### tests/test_browser_tui.py (servers list / passwords / CVE-2026-32634)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestBrowserConfigGeneration::test_serverlist_section_exists | COVERED | `tests/test_servers_list_v5.py::test_a_real_config_file_with_passwords_and_protocols` (reads a real `[serverlist]` file). |
| …::test_passwords_section_exists | COVERED | Same test. |
| …::test_server_count | COVERED | `tests/test_servers_list_v5.py::test_the_static_list_reads_v4s_layout`. |
| …::test_password_values | COVERED | `tests/test_servers_list_v5.py::test_a_real_config_file_with_passwords_and_protocols`. |
| TestStaticServerList::test_server_list_length | COVERED | `tests/test_servers_list_v5.py::test_the_static_list_reads_v4s_layout`. |
| …::test_server_fields | COVERED | `ServerEntry` field set asserted by `test_servers_list_v5.py::test_serverslist_never_carries_a_credential` (no username/password by design). |
| …::test_server_names | COVERED | `tests/test_servers_list_v5.py::test_the_static_list_reads_v4s_layout`. |
| …::test_server_protocols | OBSOLETE | §1.1 (REST only; protocol ignored). |
| …::test_server_type_is_static | COVERED | `tests/test_servers_list_v5.py::test_a_real_config_file_with_passwords_and_protocols` (`password_for` returns the static password, which `servers_list_v5.password_for` only does for `source == "static"`). |
| …::test_server_initial_status | PORT | Not asserted. Port: `servers_list_v5.load_static_servers(config)` entries start with `status == servers_list_v5.UNKNOWN`. |
| …::test_server_default_username | PORT | Not asserted. Port: the browser poller's token request (`client_v5.RemoteConnection`, default `username="glances"`) uses `glances` when `-u` is not given. |
| …::test_server_default_empty_password | OBSOLETE | v5 entries hold no credential (P3 design, `ServerEntry`), asserted by `test_serverslist_never_carries_a_credential`. |
| TestPasswordList::test_host_specific_password | COVERED | `tests/test_servers_list_v5.py::test_a_configured_password_opens_a_protected_server`, `::test_a_real_config_file_with_passwords_and_protocols`. |
| …::test_loopback_password | COVERED | Same lookup by host: `::test_a_configured_password_opens_a_protected_server`. |
| …::test_default_fallback | COVERED | `tests/test_servers_list_v5.py::test_a_real_config_file_with_passwords_and_protocols` (`beta` → `dflt`). |
| …::test_no_password_without_default | PORT | Not asserted. Port: `ServersPoller([], _Config(passwords={"alpha": "x"}), []).password_for(ServerEntry(name="beta", port=61208)) is None`. |
| TestColumnsDefinition::test_columns_loaded | COVERED | `tests/test_servers_list_v5.py::test_columns_parse_v4s_syntax`. |
| …::test_columns_structure | COVERED | Same (`Column(plugin, field, key)`). |
| …::test_columns_values | COVERED | Same. |
| TestGetUriStatic::test_uri_without_password | OBSOLETE | v4 credential-in-URI scheme removed with XML-RPC (§1.1); v5 never puts credentials in a URL: `tests/test_phase3_cve_v5.py::test_the_client_url_never_carries_credentials`, `tests/test_client_v5.py::test_the_password_never_goes_into_a_url`. |
| …::test_uri_with_password | OBSOLETE | Same (and inverted: credentials in the URI are now forbidden). |
| …::test_uri_protected_uses_saved_password | COVERED | `tests/test_servers_list_v5.py::test_a_configured_password_opens_a_protected_server`. |
| …::test_uri_protected_default_fallback | COVERED | Same test (`default` case). |
| …::test_uri_static_uses_name_not_ip | COVERED | `tests/test_servers_list_v5.py::test_the_static_list_reads_v4s_layout` (`target` built from the configured name). |
| TestGetUriDynamic::test_uri_dynamic_uses_ip_not_name | COVERED | `tests/test_zeroconf_v5.py::test_discovery_lists_the_v5_announcements_only` (name = address, announced name → alias). |
| …::test_uri_dynamic_protected_no_saved_password | COVERED | `tests/test_zeroconf_v5.py::test_a_discovered_server_is_sent_no_configured_credential`. |
| …::test_uri_dynamic_no_default_password_fallback | COVERED | Same test (`default` configured, nothing sent). |
| …::test_get_connect_host_static | COVERED | `tests/test_servers_list_v5.py::test_the_static_list_reads_v4s_layout`. |
| …::test_get_connect_host_dynamic | COVERED | `tests/test_zeroconf_v5.py::test_discovery_lists_the_v5_announcements_only`. |
| …::test_get_preconfigured_password_static | COVERED | `tests/test_servers_list_v5.py::test_a_non_static_server_gets_no_configured_password`. |
| …::test_get_preconfigured_password_dynamic_returns_none | COVERED | Same test. |
| …::test_get_preconfigured_password_dynamic_no_default | COVERED | Same test (default configured → None for zeroconf). |
| TestZeroconfAttackScenario::test_attacker_advertised_server_no_credential_leak | COVERED | `tests/test_zeroconf_v5.py::test_a_discovered_server_is_sent_no_configured_credential`, `::test_a_discovered_server_never_shares_a_static_servers_connection`. |

### tests/test_glances_curses.py (v4 TUI)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestDisplayTopHelpers::test_get_stats_summary | OBSOLETE | v4 `__display_top` internals, replaced by `curses_renderer_v5` + `TuiV5._build_fitted_frame` (§1.4). Visible behaviour covered by `test_curses_v5.py::test_top_row_gaps_evenly_distributes_remaining_space`. |
| …::test_compute_spacing_single_plugin | OBSOLETE | Same; `tests/test_curses_v5.py::test_top_row_gaps_handles_single_block`. |
| …::test_compute_spacing_disables_optional_stats | OBSOLETE | Same; narrow-terminal degradation in `tests/test_curses_v5.py::test_narrow_terminal_drops_load_never`, `::test_degrade_steps_order`. |
| …::test_get_plugin_width | OBSOLETE | Same; `tests/test_curses_renderer_v5.py::test_pluginblock_height_and_width`. |
| …::test_handle_quicklook_plugin_unavailable | OBSOLETE | v4 `stats.get_plugin` path; v5 builds the frame from the registry (`test_curses_renderer_v5.py::test_build_frame_skips_zero_row_top_block`). |
| TestGlancesTextbox::test_backspace_deletes_previous_character | COVERED | `tests/test_curses_v5.py::test_every_backspace_a_terminal_sends_erases` (127, 8, KEY_BACKSPACE). |
| TestGlancesTextbox::test_enter_finishes_editing | COVERED | `tests/test_curses_v5.py::test_every_enter_a_terminal_sends_submits`. |
| TestCursorDisable::test_process_name_left_is_noop_when_cursor_disabled | PORT | v5 `test_disable_cursor_neutralises_every_key_that_needs_a_target` checks UP/DOWN/k/+/- only. Port: `TuiV5(disable_cursor=True)._handle_key(curses.KEY_LEFT) == "ignored"`, `_view.command_offset` unchanged (`glances_curses_v5.py`, `command_left` is a `cursor: True` entry). |
| TestCursorDisable::test_process_name_right_is_noop_when_cursor_disabled | PORT | Same with `KEY_RIGHT`. |
| TestCursorDisable::test_process_name_right_advances_when_cursor_enabled | COVERED | `tests/test_curses_v5.py::test_the_command_arrows_scroll_and_floor_at_zero`. |
| TestCursorDisable::test_process_name_left_decrements_when_cursor_enabled | COVERED | Same test. |
| TestLoadConfigPrecedence::test_disable_separator_flag_beats_config | COVERED | `tests/test_curses_v5.py::test_disable_separator_suppresses_the_rule` (config default `True`), `::test_disable_unicode_flag_beats_separator_config`. |
| …::test_disable_bg_flag_beats_config | COVERED | `tests/test_curses_v5.py::test_disable_bg_flag_or_config`. |
| …::test_config_applies_when_no_flag_is_given | PORT | Separator half COVERED (`test_curses_v5.py::test_separator_disabled_paints_nothing`); `[outputs] disable_bg=True` without the flag → `TuiV5._disable_bg is True` is not asserted (`glances_curses_v5.py:583`). |
| …::test_defaults_are_kept_when_the_keys_are_absent | COVERED | `tests/test_curses_v5.py::test_separator_default_enabled_uses_box_drawing_char` (separator on); `_disable_bg` default False folded into the port above. |

### tests/test_webui.py (Selenium, v4 server)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_screenshot | PORT | No real-browser test of the v5 UI. Point the `glances_webserver` fixture at `glances-v5 -s` (it starts v4 today) and keep the multi-resolution screenshots (no assertion; manual review). Low priority. |
| test_loading_time | PORT | Phase 4 "performance validation": no v5 equivalent. Same Selenium harness on `/` of `glances-v5 -s` (`webserver_v5._wire_webui`, `glances5.js`), backend < 2000 ms, DOM complete < 2000 ms. |
| test_title | PORT | `test_webserver_v5.py::test_index_is_served_when_the_webui_is_enabled` checks `glances5.js` only. Port: `GET /` contains `<title>Glances</title>` (`templates/index_v5.html`). |
| test_plugins | COVERED | `tests/test_webui_v5_render.py::test_the_registry_renders_every_registered_plugin` (node render probe over the built bundle). |

### tests/test_webui_template_response.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_template_response_supports_old_starlette_signature | OBSOLETE | v5 serves the index as a static `FileResponse`, no Jinja2 (`webserver_v5._wire_webui` docstring "No Jinja2"). |
| test_template_response_supports_new_starlette_signature | OBSOLETE | Same. |
| test_index_uses_template_helper_for_new_starlette_signature | GAP | The template mechanics are obsolete, but the asserted behaviour — `/?refresh=7` sets the WebUI cadence (documented in `docs/api/restful.rst` "WebUI refresh") — has no v5 equivalent: `js/v5/api.js` starts at `[global] refresh`, `js/v5/refresh.js` only offers the footer stepper + localStorage. No decision drops the URL parameter. |
| test_browser_uses_template_helper_for_old_starlette_signature | OBSOLETE | No Jinja2; `/browser` is a static page (`test_webui_v5_browser.py::test_browser_page_is_served_with_server_browser_only`). |
| test_index_renders_with_installed_jinja2_templates | OBSOLETE | No Jinja2 (its `?refresh=9` assertion is the same GAP as above, counted once). |

### tests/test_limits_no_credential_leak.py (GHSA-2jqf-3j6f-683p — limits)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_no_secret_in_all_limits | COVERED | v5 `get_limits()` reads a closed key space (`<field>_<level>`, `<pk>_<field>_<level>`) and no plugin overrides it (grep: only `base_v5.py:946`), so section credentials never enter the limits. Asserted by `tests/test_plugin_base_v5_limits.py::test_get_limits_never_leaks_action_or_control_keys_or_values`, `::test_per_item_limits_never_leak_the_action_value`. Optional hardening: same canary with real `ip`/`ports` sections through `/api/5/all/limits`. |
| test_sensitive_keys_are_redacted | OBSOLETE | v4 copies every option then redacts; v5 never copies non-threshold options (design §7 comment in `base_v5.get_limits`). Leak property covered above. |
| test_url_userinfo_is_redacted | OBSOLETE | Same. |
| test_other_limits_are_unchanged | OBSOLETE | v5 limits deliberately exclude `refresh`, descriptions, flags (`test_plugin_base_v5_limits.py::test_get_limits_never_leaks_action_or_control_keys_or_values` asserts `refresh`/`disable` absent). |
| test_option_names_without_plugin_prefix | OBSOLETE | `user`/`token` never enter v5 limits; `user_careful` → threshold is covered by `tests/test_plugin_base_v5_limits.py::test_get_limits_layers_config_over_defaults_per_level`. |
| test_plugin_still_reads_the_real_values | COVERED | `tests/test_plugin_ip_v5.py::test_fetch_uses_basic_auth_when_credentials_set` (ip uses the real credentials); `tests/test_ports_no_credential_leak_v5.py` for `[ports]`. |

### tests/test_main.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestGlancesMain::test_fs_free_space_from_config | COVERED | v5 reads `[fs] free_space` in the plugin, independently of mode: `tests/test_plugin_fs_v5.py::test_free_space_reads_config_key`; overlay `tests/test_main_v5.py::test_fs_free_space_flag_overlays_the_config`. |

### tests/test_stdout.py

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_stdout_selectors (5 params) | COVERED | `tests/test_stdout_v5.py::test_parse_selection_keeps_dotted_keys_whole` (plugin, plugin.attr, plugin.dotted.key.attr — the VLAN `eth0.100` case is the same rule). |

### tests/test_stdout_csv.py (issue #3606)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_list_plugin_steady_state | COVERED | `tests/test_stdout_v5.py::test_csv_prints_the_header_first_then_aligned_data`. |
| test_list_plugin_mixed_initial_field_sets | COVERED | `tests/test_stdout_v5.py::test_csv_keeps_each_item_own_fields`. |
| test_list_plugin_interface_removed | COVERED | `tests/test_stdout_v5.py::test_csv_prints_the_header_first_then_aligned_data` (`lo` vanished → N/A). |
| test_list_plugin_interface_reappears_with_partial_fields | PORT | Not asserted in v5. Port to `stdout_v5.CsvRenderer`: item with full fields at header time, later present with fewer fields → one `N/A` per missing field, row width == header width (verified: `wlan0,7,N/A,N/A`). |
| test_list_plugin_interface_added_is_omitted | COVERED | `tests/test_stdout_v5.py::test_csv_prints_the_header_first_then_aligned_data` (`new0` gets no column). |
| test_list_plugin_added_keeps_existing_aligned | PORT | v5 test only appends the new item at the end. Port: a new item inserted **between** two header items → existing items keep their columns (verified). |
| test_dict_plugin_unaffected | PORT | v5 tests only `cpu.total`. Port: `CsvRenderer([("cpu", None)])` on a dict → 3-column header, 3-column row. |
| test_attribute_selector_unaffected | COVERED | `tests/test_stdout_v5.py::test_csv_prints_the_header_first_then_aligned_data` (`cpu.total` single column). |

### tests/test_outdated.py (CVE-2026-46607)

v5 has no PyPI version check (no `*_v5.py` imports `glances.outdated`; parity inventory `[global] check_update` ❌,
`--disable-check-update` "needs a feature v5 does not have"). §8 says the update check is **carried forward**
with a JSON cache, so this is a GAP, and these six tests are the acceptance tests of that future module.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestOutdatedCache::test_001_malicious_pickle_is_not_executed | GAP | No v5 version-check module. Required by §8 CVE-2026-46607 when ported. |
| …::test_002_json_round_trip | GAP | Same (JSON cache, datetimes via `isoformat()`). |
| …::test_003_legacy_pickle_cache_is_ignored_gracefully | GAP | Same (legacy pickle = silent cache miss). |
| …::test_004_stale_cache_returns_empty | GAP | Same (7-day expiry). |
| …::test_005_version_mismatch_invalidates_cache | GAP | Same. |
| …::test_006_missing_cache_file_returns_empty | GAP | Same. |

### tests/test_perf.py (Phase 4 — performance validation)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_perf_update | OBSOLETE | Asserts v4 `GlancesStats.update()` serving "from cache" more often than "from update" — the passive-server cache that `--cached-time` sized, dropped by decision (§10 "Dropped — `--cached-time`", 2026-09-27; v5 scheduler always collects, §7.1). **No v5 perf equivalent exists**: Phase 4's "no regression on refresh latency" (§10 Phase 4) has no test. A new test is needed (e.g. one `AsyncScheduler` cycle over all discovered plugins under a latency budget), not a port of this one. |

### tests/test_memoryleak.py (Phase 4)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_memoryleak_no_history | PORT | v5 ships `--memory-leak` (`main_v5.apply_memory_leak_flags`, `measure_memory_leak`), but `tests/test_main_v5.py::test_measure_memory_leak_diffs_the_second_window_only` uses a fake scheduler and no threshold. Port: real `assemble()`d scheduler (all plugins, `--disable-history`, refresh 1 s), warm-up 3 s, measure 10 s with `measure_memory_leak`, assert growth / iteration < 15000 B. This is the only v5 Phase 4 memory check once ported. |

---

### Summary — counts per verdict

| v4 file | tests | SHARED | COVERED | PORT | OBSOLETE | GAP |
|---|---|---|---|---|---|---|
| test_restful.py | 23 | 0 | 10 | 1 | 5 | 7 |
| test_api.py | 6 | 0 | 5 | 1 | 0 | 0 |
| test_api_secure.py | 12 | 0 | 9 | 2 | 1 | 0 |
| test_xmlrpc.py | 16 | 0 | 3 | 7 | 6 | 0 |
| test_mcp.py | 25 | 0 | 14 | 7 | 4 | 0 |
| test_browser_restful.py | 16 | 0 | 8 | 2 | 6 | 0 |
| test_browser_tui.py | 33 | 0 | 26 | 3 | 4 | 0 |
| test_glances_curses.py | 15 | 0 | 7 | 3 | 5 | 0 |
| test_webui.py | 4 | 0 | 1 | 3 | 0 | 0 |
| test_webui_template_response.py | 5 | 0 | 0 | 0 | 4 | 1 |
| test_limits_no_credential_leak.py | 6 | 0 | 2 | 0 | 4 | 0 |
| test_main.py | 1 | 0 | 1 | 0 | 0 | 0 |
| test_stdout.py | 1 (5 params) | 0 | 1 | 0 | 0 | 0 |
| test_stdout_csv.py | 8 | 0 | 5 | 3 | 0 | 0 |
| test_outdated.py | 6 | 0 | 0 | 0 | 0 | 6 |
| test_perf.py | 1 | 0 | 0 | 0 | 1 | 0 |
| test_memoryleak.py | 1 | 0 | 0 | 1 | 0 | 0 |
| **Total** | **179** | **0** | **92** | **33** | **40** | **14** |

No test in this group is SHARED: each drives a v4-only object (v4 server subprocess, `GlancesRestfulApi`,
`GlancesStats`, `glances.config.Config`, `_GlancesCurses`, `GlancesStdoutCsv`, `glances.api`, `glances.outdated`).

## v4 -> v5 test migration audit — group 5 (exporters: SQL sanitizing, CSV/JSON/InfluxDB/TimescaleDB, snapshot isolation, .sh integration scripts)

Branch `develop-v5`, read-only audit, 2026-10-03.

### Preliminary facts

- **No v5 exporter reuses its v4 module.** None of `glances/exports/glances_*/export_v5.py` or
  `glances/exports/export_base_v5.py` imports anything from `glances/exports/glances_<name>/__init__.py`
  or `glances/exports/export.py` (grep for `from glances.exports.glances_` returns nothing). Every v4 test that
  imports a v4 `Export` or `GlancesExport` therefore tests v4-only code. The only SHARED code is the third-party
  `clickhouse_connect.driver.binding.quote_identifier`, which v5 `glances_clickhouse/export_v5.py::Export.init()` imports and uses.
- Recent v4 fixes already ported to v5 by commit `3237187` ("v5: port v4 fixes from develop"):
  #3755 duckdb `normalize(['False'])` and #3757 influxdb dotted item keys, each with a v5 test.
  #3753 (json flush) does not apply: v5 JSON `update()` builds the buffer and writes it in one pass.
  #3761 (csv stable columns) is replaced by v5's rotation design. #3767 (snapshot isolation) holds in v5
  by construction (`get_export()` projects new dicts, `_merge_limits()`/`_inject_key()` build new dicts), but no test asserts it.
  The timescaledb list fix (#3592 column/value count, `key` -> `key_id`) holds in v5 `_rows()`, but only part of it is asserted.
- Environment: `duckdb` is **not installed** in this venv. So `tests/test_duckdb_sanitize.py` skips entirely, and the
  v5 real-database tests (`tests/test_export_wave_d_v5.py::test_duckdb_real_database_stores_hostile_strings_as_data`,
  `tests/test_phase3_cve_v5.py::test_duckdb_stores_hostile_names_as_data_on_a_real_database`) also skip. The
  fake-driver test `tests/test_export_wave_d_v5.py::test_duckdb_binds_every_value_and_quotes_every_identifier` runs.
  `clickhouse_connect` and `psycopg` are installed. Run results: v4 group: 16 passed, 1 skipped. Relevant v5 files: 150 passed, 19 skipped.
- `tests/export_fakes_v5.py::HOSTILE_NAME = "x'); DROP TABLE cpu; --\"`\\"` contains a space, `;`, `)`, one `"`, a backtick and a backslash.
  `tests/test_phase3_cve_v5.py::HOSTILE` has 9 payloads, including `'x"); DROP TABLE canary; --'`, `"é ✓'); …"` and `"%s %(x)s ? :1 {0}"`.

---

### tests/test_duckdb_sanitize.py (v4 `glances.exports.glances_duckdb._quote_identifier` / `Export`)

v5 target: `glances/exports/glances_duckdb/export_v5.py` (`quote_identifier`, `normalize`, `Export._rows`, `Export._write`).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestQuoteIdentifier::test_simple_name | COVERED | `tests/test_export_wave_d_v5.py::test_duckdb_binds_every_value_and_quotes_every_identifier` asserts `CREATE TABLE "fakecollection" ("time" TIMETZ, "hostname_id" VARCHAR, "key_id" VARCHAR, ` |
| TestQuoteIdentifier::test_name_with_spaces | COVERED | same test: `HOSTILE_NAME` (contains spaces) must appear as `'"' + HOSTILE_NAME.replace('"','""') + '" DOUBLE'` |
| TestQuoteIdentifier::test_name_with_double_quote | COVERED | same assertion (embedded `"` doubled) |
| TestQuoteIdentifier::test_name_with_multiple_double_quotes | PORT | No v5 input has more than one `"`. Assert `quote_identifier('a"b"c') == '"a""b""c"'` (`glances_duckdb/export_v5.py::quote_identifier`). Cheap: add it to a parametrized unit test. |
| TestQuoteIdentifier::test_sql_injection_attempt | COVERED | `HOSTILE_NAME` contains `'); DROP TABLE cpu; --` (wave_d fake test above). Also `tests/test_phase3_cve_v5.py::test_duckdb_stores_hostile_names_as_data_on_a_real_database` (real DB, skips without duckdb) |
| TestQuoteIdentifier::test_empty_string | PORT (low) | `quote_identifier('') == '""'` is not asserted in v5 |
| TestQuoteIdentifier::test_non_string_input | PORT (low) | v5 `quote_identifier` still does `str(name)`. Assert `quote_identifier(42) == '"42"'` |
| TestQuoteIdentifier::test_name_with_semicolon | COVERED | `HOSTILE_NAME` contains `;` (wave_d quoting assertion) |
| TestQuoteIdentifier::test_name_with_parentheses | COVERED | `HOSTILE_NAME` contains `)` (wave_d quoting assertion) |
| TestDuckDBInjectionPrevention::test_export_normalized_boolean | COVERED | `tests/test_export_wave_d_v5.py::test_duckdb_normalize_keeps_false_values` (port of #3755). v5 never asserts a BOOLEAN column round-trip in a real DB, which is optional. |
| …::test_create_table_with_safe_names | COVERED | `tests/test_export_wave_d_v5.py::test_duckdb_real_database_stores_hostile_strings_as_data` (benign `fakescalar` table, `("busy host", 12.5)` read back) |
| …::test_create_table_with_special_column_names | COVERED | `tests/test_phase3_cve_v5.py::test_duckdb_stores_hostile_names_as_data_on_a_real_database` (hostile field names with spaces become columns) and the wave_d fake test |
| …::test_injection_in_column_name_is_neutralized | COVERED | `tests/test_phase3_cve_v5.py::test_duckdb_stores_hostile_names_as_data_on_a_real_database` (canary table survives; `hostile in columns`), `tests/test_export_wave_d_v5.py::test_duckdb_real_database_stores_hostile_strings_as_data` (tables `cpu`/`y` neither created nor dropped). Both skip without duckdb; the fake test runs. |
| …::test_injection_in_table_name_is_neutralized | PORT (security) | No v5 test uses a hostile **table** (plugin) name. In v5 `plugin_name` is a code constant, so it is not attacker-controlled, but the rule requires a test. Call `Export._write('x (a INT); DROP TABLE important; --', columns, rows)` (or build a fake plugin with that `plugin_name`). Assert, on the fake connection, that the CREATE/INSERT text starts with the doubled-quote identifier. On a real DB, assert that the canary table survives. |
| …::test_insert_with_quoted_table | PORT (low) | Hyphenated table name `my-plugin` through `Export._write`. Fold it into the table-name test above. |
| …::test_full_export_simulation | COVERED | `tests/test_export_wave_d_v5.py::test_duckdb_real_database_stores_hostile_strings_as_data` and `::test_duckdb_binds_every_value_and_quotes_every_identifier` (full v4 layout `time, hostname_id, key_id, fields…`) |
| …::test_column_with_double_quote_in_name | COVERED | wave_d fake quoting assertion (`HOSTILE_NAME` has `"`), and phase3 `'x"); DROP TABLE canary; --'` |

### tests/test_clickhouse_sanitize.py (GHSA-2hvx-g9v6-w29h)

v5 target: `glances/exports/glances_clickhouse/export_v5.py`. v5 is stronger than v4: `_SAFE_IDENTIFIER` **refuses** names with a backtick, quote, backslash or control character, and only then applies `quote_identifier`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestQuoteIdentifier::test_simple_name_unchanged | SHARED | Exercises only `clickhouse_connect.driver.binding.quote_identifier`, which v5 `Export.init()` imports unchanged. The file imports v4 `glances.exports.glances_clickhouse.Export` at module level, so when v4 is deleted, move these two tests (or drop that import). |
| TestQuoteIdentifier::test_backtick_is_escaped | SHARED | Same driver function. Note: `tests/test_export_wave_c_v5.py` replaces it with a fake, so the real escaping is asserted only here. |
| TestClickHouseExportDDL::test_benign_create_table | COVERED | `tests/test_export_wave_c_v5.py::test_clickhouse_creates_typed_tables_and_inserts_rows` (`CREATE TABLE IF NOT EXISTS \`fakescalar\``, `` `total` Nullable(Float64) ``, inserts) |
| TestClickHouseExportDDL::test_injection_in_column_name_is_neutralized | COVERED | `tests/test_export_wave_c_v5.py::test_clickhouse_hostile_names_never_reach_the_sql`: a config key ``x` Int8) ENGINE=Log; DROP TABLE cpu; --`` becomes a column name (the same backtick breakout + ENGINE payload class). Asserts no `DROP` in any SQL and that the column is refused. Monitored names (`HOSTILE_NAME`) only travel as row data. |
| TestClickHouseExportDDL::test_injection_in_plugin_name_is_neutralized | PORT (security) | No v5 test passes a hostile table name. Assert that `Export.export(INJECTION, ['time','hostname_id'], [[now,'h']])` sends **no** command, query or insert to the client (`_SAFE_IDENTIFIER.fullmatch(name)` refuses it), and that a benign name with a space is quoted. Use the wave_c fake backend with the real `quote_identifier` if available. |

Side note: GHSA-2hvx-g9v6-w29h (ClickHouse) is not listed in `docs/architecture/glances-v5-architecture-decisions.md` §8, though v5 carries a fix.

### tests/test_export_csv_columns.py (#3761)

v5 target: `glances/exports/glances_csv/export_v5.py`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_csv_columns_remain_aligned_when_interfaces_change | OBSOLETE | v4 #3761 keeps the first header and fills vanished columns with `''` (and drops new ones). v5 deliberately **rotates** to `<base>-NNN.csv` on any column-set change (module docstring "one deliberate departure"). Same column set in another order is realigned. The property the v4 test protects (every row as wide as its header, a column keeps its identity) is asserted by `tests/test_export_csv_v5.py::test_csv_width_guard_every_written_row_matches_header_width`, `::test_csv_mid_run_divergence_logs_warning_and_rotates` and `::test_csv_reordered_items_keep_the_file_and_the_column_alignment`. Caveat for the maintainer: the rotation decision is recorded only in code/test docstrings. g8 spec §9 had suggested v4-style blank fill, and §7 of the decisions doc says nothing about it. With interfaces that come and go (VPN, docker veth), v5 produces one file per change. Confirm this is wanted rather than adopting the #3761 behaviour. |
| test_existing_header_compatibility_is_preserved [compatible=True / False] | COVERED | True: `tests/test_export_csv_v5.py::test_csv_appends_to_an_existing_file_with_a_matching_header` (3 rows). False: `::test_csv_startup_mismatch_rotates_instead_of_refusing` (original file byte-identical, new data goes to `-001`) |

### tests/test_export_influxdb_normalize.py (#3757)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_dotted_list_item_keys_remain_separate_measurements | COVERED | `tests/test_export_base_v5.py::test_normalize_for_influxdb_keeps_dotted_item_keys_as_separate_measurements` (2 measurements, `interface_name` tags `eth0.100`/`eth0.200`, fields `{key, rx}`). The fix is in `GlancesExportBase.normalize_for_influxdb` (commit 3237187). |

### tests/test_export_json.py (#3753)

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_json_export_writes_a_single_sample | COVERED | `tests/test_export_json_v5.py::test_json_writes_one_object_per_cycle`: a single `update()` writes the file. v5 has no sentinel-based flush (`glances_json/export_v5.py::update`). The v4 test is an end-to-end CLI run (`python -m glances … --stop-after 2 --quiet`). Its v5 equivalent cannot be written today: **`glances-v5 --quiet` ignores `--stop-after`** (`main_v5.py` help says "TUI and stdout modes"; verified: `python -m glances.main_v5 -C empty.conf --export json --export-json-file X --stop-after 2 --quiet --disable-plugin all --enable-plugin cpu,mem` was still running at a 40 s timeout, though the JSON file was written). See the GAP note below. |

### tests/test_export_snapshot_isolation.py (#3767)

v5 targets: `glances/exports/export_base_v5.py` (`_merge_limits`, `_inject_key`, `update`) and `glances/plugins/plugin/base_v5.py::get_export`.

| v4 test | verdict | evidence / what to port |
|---|---|---|
| test_prepared_payloads_are_detached_from_plugin_stats | PORT | v4 `_prepare_export_stats` is v4-only. Its v5 counterpart is `_merge_limits` (+ `_inject_key`). Dropping `<plugin>_disable` is already covered by `tests/test_export_base_v5.py::test_merge_limits_drops_the_disable_key`. No test asserts that the result is a new object and that the input dict, list and list items are **unchanged** after `_merge_limits` / `_inject_key`. Add that assertion for a dict and a list payload. |
| test_export_preparation_does_not_mutate_live_stats | PORT | After `exporter.update([scalar, collection])` with limits configured, assert that `plugin.get_export()` (and the `StatsStoreV5` entry) still carries no `<plugin>_*` limit key, `history_size` or injected `key`. Run it against `GlancesExportBase.update` and against the overriding `update()`s (csv, duckdb, timescaledb `_rename_user`, clickhouse). |

### tests/test_export_timescaledb_list.py (#3592, transaction recovery)

v5 target: `glances/exports/glances_timescaledb/export_v5.py` (`Export._rows`, `Export._write`).

| v4 test | verdict | evidence / what to port |
|---|---|---|
| TestTimescaleDBListPlugin::test_columns_and_values_count_match | PORT | `tests/test_export_wave_d_v5.py::test_timescaledb_binds_every_value_and_quotes_every_identifier` checks slices of the collection rows only. Assert `len(row) == len(columns)` for every collection row, either from `Export._rows('network', payload)` or by counting `%s` placeholders against the row length in the fake INSERT. |
| TestTimescaleDBListPlugin::test_key_field_exported_once_as_key_id | PORT | `key_id` presence is covered (CREATE prefix assertion). Absence of a `"key"` column is not asserted. Assert that `'"key" '` is not in the fakecollection CREATE (or that `key` is not among `_rows()` column names). |
| TestTimescaleDBListPlugin::test_no_stat_field_is_dropped | PORT | Assert the full collection row maps column -> value, including the LAST field (in v5 that is the merged `history_size`/limits). Today only `row[2:5]` is checked. |
| test_failed_insert_is_rolled_back_before_next_export | COVERED | `tests/test_export_wave_d_v5.py::test_timescaledb_failing_write_is_one_warning_per_plugin` asserts `events == ["rollback", "rollback"]` (`with client.transaction()`). Optional extension: a successful write after the failure commits. |

### tests/test_export_*.sh (Docker / live integration scripts)

All nine launch **v4**: `.venv/bin/python -m glances … --stop-after N --quiet` (`glances/__main__.py`, v4). None calls `glances-v5` or `glances.main_v5`. The decision record says: g8 spec §10, "The v4 `tests/test_export_*.sh` Docker scripts stay on v4, untouched. Rewriting them against v5 belongs to Phase 4 hardening."

Makefile: `test-export-csv`, `-json`, `-influxdb-v1`, `-influxdb-v3`, `-timescaledb`, `-nats` and `-clickhouse` each run one script. **duckdb and prometheus have no dedicated target** and run only through `test-exports` (a loop over `tests/test_export_*.sh`). No GitHub workflow runs them; `make test` (pytest) does not either.

**Blocker for every port except prometheus:** `glances-v5 --quiet` does not honour `--stop-after` (see the json note). The scripts rely on it to terminate. Expected counts (`csvcheck -l 9`, `SERIE_COUNT -eq 9`) also need re-tuning. v5 exports on its own `[export] refresh` loop, and the v5 CSV defers its header by one warm-up cycle.

| script | verdict | how it launches / what it checks / what to port |
|---|---|---|
| test_export_clickhouse.sh | PORT | Runs a clickhouse-server container; `python -m glances --config ./conf/glances.conf --export clickhouse --stop-after 10 --quiet`; `SELECT * FROM cpu FORMAT CSV` -> `csvcheck.py -l 8`. Port: run `glances-v5`. Needs `--stop-after` in quiet mode. |
| test_export_csv.sh | PORT | `python -m glances --export csv --export-csv-file /tmp/glances.csv --stop-after 10 --quiet`; `csvcheck.py -l 9`. Port: `glances-v5`, re-tune the line count (warm-up deferral), and check that no `-NNN` rotation file appears. |
| test_export_duckdb.sh | PORT | Rewrites `database=:memory:` -> `/tmp/glances.db` in a conf copy; `--export duckdb --stop-after 10 --quiet`; `duckdbcheck.py -l 9`. No Makefile target of its own. |
| test_export_influxdb_v1.sh | PORT | influxdb:1.12 container, creates the `glances` DB; `--export influxdb --stop-after 10 --quiet` (default conf lookup); checks that measurements > 0 and that `SELECT * FROM cpu` has exactly 9 rows. |
| test_export_influxdb_v3.sh | PORT | influxdb:3-core container, admin token sed into `/tmp/glances.conf`; `--export influxdb3 --stop-after 10 --quiet`; checks that the table count grew and that `cpu` has 9 rows. |
| test_export_json.sh | PORT | `--export json --export-json-file /tmp/glances.json --stop-after 3 --quiet`; `jq` on `.cpu.total`, `.mem.total`, `.processcount.total` (jq exits 0 even on null, so this is weak). |
| test_export_nats.sh | PORT | nats + nats-box subscriber on `glances.>`; `--export nats --stop-after 10 --quiet`; at least 10 messages received. |
| test_export_prometheus.sh | PORT | `--export prometheus --stop-after 10 --quiet &`, sleep 6, `curl :9091/metrics`, kill. Does not depend on `--stop-after` terminating, so it can be ported to `glances-v5` today. No Makefile target of its own. |
| test_export_timescaledb.sh | PORT | timescaledb-ha:pg17 container, creates DB `glances`; `--export timescaledb --stop-after 10 --quiet`; `SELECT * from cpu` -> `csvcheck.py -l 9`. |

#### GAP found while auditing (not a test item, blocks the .sh ports and a CLI port of test_export_json.py)

- `glances/main_v5.py`: `--stop-after` is wired only into the curses TUI and `StdoutV5` (lines ~1126, ~1264). In `--quiet`/`--no-tui` mode the process never stops. v4 stops in quiet mode, and every v4 `test_export_*.sh` depends on it. Decisions doc §11 lists `--stop-after` as shipped (v4 parity) with no exception for quiet mode.

---

### Summary

| v4 file | items | SHARED | COVERED | PORT | OBSOLETE | GAP |
|---|---|---|---|---|---|---|
| test_duckdb_sanitize.py | 17 | 0 | 12 | 5 | 0 | 0 |
| test_clickhouse_sanitize.py | 5 | 2 | 2 | 1 | 0 | 0 |
| test_export_csv_columns.py | 2 | 0 | 1 | 0 | 1 | 0 |
| test_export_influxdb_normalize.py | 1 | 0 | 1 | 0 | 0 | 0 |
| test_export_json.py | 1 | 0 | 1 | 0 | 0 | 0 |
| test_export_snapshot_isolation.py | 2 | 0 | 0 | 2 | 0 | 0 |
| test_export_timescaledb_list.py | 4 | 0 | 1 | 3 | 0 | 0 |
| test_export_*.sh (9 scripts) | 9 | 0 | 0 | 9 | 0 | 0 |
| **Total** | **41** | **2** | **18** | **20** | **1** | **0** |

Plus one non-item GAP: `main_v5` `--stop-after` ignored with `--quiet`.
