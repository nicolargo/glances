// Glances v5 WebUI -- the right column's vertical row budget.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it -- the same
// contract degrade.js and processlist_columns.js state in their own headers.
//
// A port of glances/outputs/curses_renderer_v5.py's `plan_right_column`
// (:969), `_split_workloads` (:923) and `_alert_block_height` (:610).
// tests/test_webui_v5_row_budget_drift.py runs BOTH solvers over a case matrix
// and requires identical output -- the existing drift tests compare constant
// lists, which cannot express an algorithm. Never edit one side alone.

const NOMINAL_WORKLOADS = 10; // curses_renderer_v5.py:877
const NOMINAL_ALERTS = 10; // :878
const NOMINAL_PROCESSES = 20; // :879
const MAX_WORKLOADS = 20; // :881

// Shrink ladder a->k (:947-959). `null` marks the "truncate amps to whatever
// is left" step (j).
const SHRINK_STEPS = [
	["workloads", 5], // a
	["alerts", 5], // b
	["processes", 10], // c
	["workloads", 3], // d
	["alerts", 3], // e
	["processes", 5], // f
	["workloads", 0], // g -- block hidden entirely
	["alerts", 0], // h -- header only
	["processes", 3], // i
	["amps", null], // j -- truncated, "+N lines" marker kept
	["processes", 1], // k -- beyond this the terminal clips
];

// Max-min fairness: an equal share first, then whatever one block does not use
// goes to the other, so 2 VMs beside 30 containers still show both. The odd
// leftover is offered to vms first, matching RIGHT_SLOT order.
export function splitWorkloads(quota, nVms, nContainers) {
	const share = Math.floor(quota / 2);
	let vms = Math.min(nVms, share);
	let containers = Math.min(nContainers, share);
	let leftover = quota - vms - containers;
	if (leftover > 0) {
		const take = Math.min(leftover, nVms - vms);
		vms += take;
		leftover -= take;
	}
	if (leftover > 0) containers += Math.min(leftover, nContainers - containers);
	return [vms, containers];
}

// Title row + column-header row + data rows, collapsing to a single line when
// there is nothing to show or the ladder took every row (step h).
export function alertBlockHeight(nIncidents, quota) {
	if (nIncidents <= 0 || quota <= 0) return 1;
	return 2 + Math.min(nIncidents, quota);
}

export function planRightColumn({
	bodyHeight,
	staticHeights = {},
	ampsHeight = 0,
	nVms = 0,
	nContainers = 0,
	nProcesses = 0,
	nAlerts = 0,
	nOngoing = 0,
}) {
	const state = {
		workloads: NOMINAL_WORKLOADS,
		alerts: NOMINAL_ALERTS,
		processes: NOMINAL_PROCESSES,
		amps: ampsHeight,
	};
	// Rows the alert block may never give up while the cascade still has
	// anything else to take (:1028).
	const floorAlerts = Math.min(Math.max(0, nOngoing), NOMINAL_ALERTS);

	// Mirrors `_paint_sidebar`: the visible block heights plus one blank line
	// between blocks (:1030-1051).
	const cost = (candidate) => {
		const [vmsQ, containersQ] = splitWorkloads(candidate.workloads, nVms, nContainers);
		const heights = [];
		if (nVms && vmsQ) heights.push(1 + vmsQ);
		if (nContainers && containersQ) heights.push(1 + containersQ);
		for (const h of Object.values(staticHeights)) if (h) heights.push(h);
		if (candidate.amps) heights.push(candidate.amps);
		// A zero quota hides the block outright, header included (step l).
		if (nProcesses && candidate.processes) heights.push(1 + Math.min(nProcesses, candidate.processes));
		// The alert block is ALWAYS emitted, if only as a header line.
		heights.push(alertBlockHeight(nAlerts, candidate.alerts));
		return heights.reduce((a, b) => a + b, 0) + Math.max(0, heights.length - 1);
	};

	// One row at a time, so the result provably fills the viewport without
	// overflowing it. A no-op once the ladder is exhausted.
	const growProcesses = () => {
		while (state.processes < nProcesses && cost({ ...state, processes: state.processes + 1 }) <= bodyHeight) {
			state.processes += 1;
		}
	};

	if (cost(state) <= bodyHeight) {
		while (state.workloads < MAX_WORKLOADS && cost({ ...state, workloads: state.workloads + 1 }) <= bodyHeight) {
			state.workloads += 1;
		}
		growProcesses();
	} else {
		for (const [key, value] of SHRINK_STEPS) {
			if (key === "amps") {
				if (!state.amps) continue;
				// Truncate to what remains, keeping at least the marker line.
				const deficit = cost(state) - bodyHeight;
				state.amps = Math.max(1, state.amps - deficit);
			} else {
				const target = key === "alerts" ? Math.max(value, floorAlerts) : value;
				if (target >= state[key]) continue;
				state[key] = target;
			}
			if (cost(state) <= bodyHeight) break;
		}
		if (floorAlerts && cost(state) > bodyHeight) {
			// The floor made steps b/e/h no-ops and what is left did not cover
			// the deficit. Step l, then step m: the floor itself gives way one
			// row at a time, so the block keeps as many active alerts as fit.
			state.processes = 0;
			while (state.alerts > 0 && cost(state) > bodyHeight) state.alerts -= 1;
		}
		// The step that made it fit usually freed more than the deficit; refund
		// that slack rather than leaving blank rows at the bottom.
		growProcesses();
	}

	const [vmsQ, containersQ] = splitWorkloads(state.workloads, nVms, nContainers);
	const budget = {
		vms: vmsQ,
		containers: containersQ,
		processlist: state.processes,
		programlist: state.processes,
		alert: state.alerts,
	};
	if (state.amps !== ampsHeight) budget.amps = state.amps;
	return budget;
}
