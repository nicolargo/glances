// Glances v5 WebUI -- the options PluginProcesslist.vue and
// PluginProgramlist.vue share.
//
// The two blocks differ in exactly three places: the budget key they draw
// from, their fixed column set, and the width of the one column they do not
// share (PID vs NPROCS). Everything else -- the two composed ceilings, the
// zero-quota hide rule, the <colgroup> arithmetic, the sort underline, the
// cell formatters -- is identical, and was duplicated byte-for-byte across
// the two components. process_shared.js already extracted the pure helpers
// for the same reason; this extracts the component options.
//
// A factory rather than a plain mixin object, because the three differences
// are configuration, not a host contract to document and hope is honoured:
//
//     mixins: [processBlockMixin({ budgetKey: "processlist", columnWidth })]
//
// The host still owns `visibleFixedColumns` (processlist filters it through
// its width cascade, programlist's is constant) and its own template.

import { cellClassFor } from "./columns.js";
import { dashIfBlank, formatCpuTime, formatPercent, formatProcessBytes, formatUsername } from "./format.js";
import { HEADER_SORT_KEY, commandText, ioRate } from "./process_shared.js";
import { COL_SEPARATOR, MIN_COMMAND_WIDTH } from "./process_widths.js";

export function processBlockMixin({ budgetKey, columnWidth, wideIrixLabel }) {
	return {
		// Both values are resolved once by AppShell and handed down through its
		// provide() -- never as props on the shared `<component>` binding, which
		// would leak a DOM attribute onto the thirty other plugins that never
		// read them (AppShell.vue's provide() explains the rule).
		//
		// `maxProcessesDisplay` is `[outputs] max_processes_display`, resolved
		// from the same /api/5/config fetch as refresh/theme, so the first paint
		// is already capped. `null` means "no cap".
		//
		// `rowBudget` is the vertical quota refitVertical() allots this block
		// (row_budget.js). `{}` means no budget -- an environment without
		// measurement must never hide stats.
		inject: {
			maxProcessesDisplay: { default: null },
			rowBudget: { default: () => ({}) },
		},
		computed: {
			// The `0` key's Irix mode (v4 `disable_irix`): each CPU% divided by
			// the logical core count the model publishes as `cpucore`. Null when
			// off, or against a server too old to publish the count -- the TUI
			// twin is `irix_cores()` in processlist/render_curses_v5.py.
			irixCores() {
				const cores = this.payload?.cpucore;
				return this.serverArgs?.load_irix && Number.isInteger(cores) && cores > 0 ? cores : null;
			},
			// v4's header: `CPU%/<n>` under ten cores, the block's own wide
			// label from ten up (`CPUi` / `CPU%/C`), `irix_cpu_label()`.
			cpuLabel() {
				if (this.irixCores === null) return "CPU%";
				return this.irixCores < 10 ? `CPU%/${this.irixCores}` : wideIrixLabel;
			},
			// The full payload, in ENGINE order -- the sort is server-side
			// (glances_processes.sort_key), and this component must not re-sort.
			allRows() {
				return this.payload?.data || [];
			},
			// Two ceilings, composed. `min()` because `[outputs]
			// max_processes_display` is a hard cap that available height may never
			// raise (design 4.7) -- the browser's counterpart of the TUI's
			// row_budget(view, ..., _MAX_ROWS) fallback chain. The cap applies to
			// the payload's own order: the first N rows, never the top N by any
			// column value.
			//
			// The two predicates differ on purpose, and must not be merged: their
			// `0` means opposite things. `max_processes_display = 0` must keep
			// meaning "no cap" (`> 0`), while a row quota of 0 legitimately means
			// "hide the block entirely" (`>= 0`), the browser's counterpart of the
			// TUI's own `row_budget(...) <= 0` early return.
			rows() {
				const caps = [];
				if (Number.isInteger(this.maxProcessesDisplay) && this.maxProcessesDisplay > 0) {
					caps.push(this.maxProcessesDisplay);
				}
				if (Number.isInteger(this.rowBudget?.[budgetKey]) && this.rowBudget[budgetKey] >= 0) {
					caps.push(this.rowBudget[budgetKey]);
				}
				return caps.length ? this.allRows.slice(0, Math.min(...caps)) : this.allRows;
			},
			// Ladder steps g and l make a block vanish entirely, header included
			// (row_budget.js's `cost()`). `rows` above already renders nothing at a
			// zero quota, but CollectionBlock still paints the loading/title header
			// on an empty table unless told to hide the whole block. Tied to the
			// EXPLICIT quota, never to `rows.length === 0`: an environment without
			// measurement (`rowBudget` = `{}`) must keep showing a host with zero
			// running processes, not hide it.
			quotaHidden() {
				return this.rowBudget?.[budgetKey] === 0;
			},
			// The integer the stylesheet turns into a width. CSS does the
			// character->pixel conversion, so no JS ever measures `--gl-col`: the
			// sum is the visible fixed widths, plus one separator column between
			// cells, plus Command's floor. The table's min-width is built from it,
			// so the table overflows its container exactly when Command would fall
			// below the floor -- which is what keeps the measure-driven cascade
			// firing at the TUI's own threshold.
			fixedColsStyle() {
				const keys = this.visibleFixedColumns;
				const fixed = keys.reduce((total, key) => total + columnWidth(key), 0);
				// One separator after each fixed column, before Command.
				const separators = COL_SEPARATOR * keys.length;
				return { "--gl-fixed-cols": String(fixed + separators + MIN_COMMAND_WIDTH) };
			},
		},
		methods: {
			cellClassFor,
			// Wrapped rather than exposed raw: the `/` key (TOGGLE VIEW) decides
			// short vs full path, and reading it here keeps both templates'
			// `commandText(item)` calls unchanged. Default true -- the TUI's
			// `ViewState.process_short_name`.
			commandText(item) {
				return commandText(item, this.serverArgs?.process_short_name !== false);
			},
			formatCpuTime,
			formatPercent,
			// The CPU% cell, divided in Irix mode; its colour stays the raw
			// level's, as in the TUI.
			formatCpu(value) {
				return formatPercent(this.irixCores !== null && typeof value === "number" ? value / this.irixCores : value);
			},
			formatProcessBytes,
			formatUsername,
			ioRate,
			fmt: dashIfBlank,
			isSorted(label) {
				const key = this.serverArgs?.sort_processes_key;
				return !!key && HEADER_SORT_KEY[label] === key;
			},
			memField(item, field) {
				return item?.memory_info ? item.memory_info[field] : undefined;
			},
			// `columnWidth(key)` alone under-sizes every column by the separator.
			// Under `table-layout: fixed` the <col> width is the column's WHOLE
			// box, and `.gl-process-table td:not(:last-child)`'s `padding-right`
			// separator comes out of that same box -- so a `<col>` of exactly N
			// characters leaves only N - COL_SEPARATOR for content (every fixed
			// column crops early; invisibly so for "S", whose N=1 makes it
			// disappear rather than merely narrow). Adding COL_SEPARATOR reserves
			// the separator's own characters inside the box.
			//
			// `fixedColsStyle` above does NOT add it per column: it already
			// charges one separator per visible fixed column, so
			// Sum(N + COL_SEPARATOR) here and Sum(N) + separators there agree by
			// construction.
			colStyle(key) {
				return { width: `calc(${columnWidth(key) + COL_SEPARATOR} * var(--gl-col))` };
			},
		},
	};
}
