// Glances v5 WebUI — the poll cadence the footer's -/+ buttons step through,
// and where a viewer's choice is remembered.
//
// Deliberately NOT in api.js: none of this talks to /api/5. `[global]
// refresh` stays the cadence a page STARTS at; this module owns what the
// viewer does with it afterwards.

// A fixed ladder rather than +/- 1 s: the whole 1..60 s range is then seven
// clicks wide instead of fifty-eight, and every rung is a cadence someone
// would actually pick.
export const REFRESH_STEPS = [1, 2, 3, 5, 10, 15, 30, 60];

const STORAGE_KEY = "glances.refresh";

export function stepRefresh(seconds, direction) {
	// `seconds` need not be a rung: `[global] refresh=4` is legal, and so is a
	// value outside the ladder entirely. Stepping from it lands on the nearest
	// rung in the requested direction (4 -> 5 up, 4 -> 3 down), and both ends
	// clamp rather than wrap -- a "+" that jumped back to 1 s would be a trap.
	const last = REFRESH_STEPS[REFRESH_STEPS.length - 1];
	if (direction > 0) {
		return REFRESH_STEPS.find((step) => step > seconds) ?? last;
	}
	return REFRESH_STEPS.filter((step) => step < seconds).pop() ?? REFRESH_STEPS[0];
}

export function loadRefresh() {
	// null, never a number, when nothing is stored: the caller then keeps
	// `[global] refresh`. A stored value that does not parse is treated the
	// same way rather than being repaired -- only saveRefresh() writes this
	// key, so anything else in it is not ours.
	try {
		const seconds = Number(globalThis.localStorage.getItem(STORAGE_KEY));
		return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
	} catch {
		// No localStorage at all (private mode, disabled site data, the render
		// probe's DOM stub). The cadence simply does not survive the reload.
		return null;
	}
}

export function saveRefresh(seconds) {
	try {
		globalThis.localStorage.setItem(STORAGE_KEY, String(seconds));
	} catch {
		// Same as above -- never a reason to make the click fail.
	}
}
