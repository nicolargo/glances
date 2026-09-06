// Glances v5 WebUI — the only module that talks to /api/5.
//
// Three things components must not each reinvent:
//
// 1. `fetch` does NOT reject on 4xx/5xx. Only a network failure rejects, so a
//    500 carrying a JSON error body parses cleanly and looks like data.
// 2. Nor does a status check catch a 200 whose BODY is the wrong shape
//    (FastAPI's `{"detail": ...}`). G9-1's diagnostic page reported a
//    plausible, wrong plugin count for exactly this reason. Hence `validate`.
// 3. Endpoint outcomes must be independent: one plugin's failure must not
//    blank the page.

export const DEFAULT_REFRESH_SECONDS = 2;
export const DEFAULT_THEME = "dark";
const VALID_THEMES = new Set(["dark", "light"]);

export async function getJson(path) {
	const response = await fetch(path);
	if (!response.ok) {
		throw new Error(`${path}: HTTP ${response.status}`);
	}
	return response.json();
}

export function validate(payload, spec) {
	// `200 null` means the plugin has registered but has not published yet
	// (scheduler cycle 0) -- the G9-1 route contract. A loading state, not a
	// shape error; the caller renders it as such.
	if (payload === null || payload === undefined) return payload;

	if (spec.shape === "collection") {
		if (typeof payload !== "object" || !Array.isArray(payload.data)) {
			throw new Error("unexpected shape: expected a collection envelope with a data array");
		}
		// An empty collection is legitimate (no container running, no folder
		// configured). Only a NON-empty one can be checked for fields.
		const first = payload.data[0];
		if (first) requireFields(first, spec.required);
		return payload;
	}

	if (typeof payload !== "object" || Array.isArray(payload)) {
		throw new Error("unexpected shape: expected a scalar payload object");
	}
	requireFields(payload, spec.required);
	return payload;
}

function requireFields(obj, required) {
	const missing = (required || []).filter((field) => !(field in obj));
	if (missing.length) {
		throw new Error(`unexpected shape: missing ${missing.join(", ")}`);
	}
}

export async function resolveConfig() {
	// [global] refresh and [outputs] theme, both via the SAME /api/5/config
	// fetch. NOT /api/5/args: measured in G9-1, the v5 argument namespace
	// carries no refresh key at all.
	let config;
	try {
		config = await getJson("api/5/config");
	} catch {
		// Only a failure to REACH the config falls back. A UI that cannot read
		// the cadence still polls at the default rather than not polling at
		// all, and stays on the default theme rather than going unstyled.
		// Anything thrown by the extraction below is a programming error and
		// must surface, not be disguised as an unreachable server.
		return { refreshSeconds: DEFAULT_REFRESH_SECONDS, theme: DEFAULT_THEME };
	}
	const refresh = config && config.global && config.global.refresh;
	const seconds = Number(refresh);
	const refreshSeconds = Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_REFRESH_SECONDS;

	// A typo or unrecognised value must not be written through to
	// data-theme -- fall back to the same default `[outputs] theme` itself
	// uses (glances_curses_v5.py:226) rather than shipping an unstyled page.
	const rawTheme = config && config.outputs && config.outputs.theme;
	const theme = VALID_THEMES.has(rawTheme) ? rawTheme : DEFAULT_THEME;

	return { refreshSeconds, theme };
}

export async function fetchAll(specs) {
	// ONE request per tick, not one per plugin. At 34 components and a 2 s
	// cadence, per-plugin fan-out is 17 req/s per open tab against a loop v4
	// hits once. /api/5/all already applies the export filter and keeps
	// `_levels`, so this is a drop-in.
	//
	// The trade, stated plainly: a single failure now blanks every plugin
	// instead of one. That is pinned by a test.
	let all;
	try {
		all = await getJson("api/5/all");
	} catch (e) {
		const errors = {};
		specs.forEach((s) => {
			errors[s.name] = e.message;
		});
		return { results: {}, errors };
	}

	if (!all || typeof all !== "object" || Array.isArray(all)) {
		// getJson guarantees only "HTTP 2xx and parseable JSON" -- `null`, a
		// number, a string and an array all satisfy that. `spec.name in all`
		// would then throw a TypeError out of fetchAll, breaking its own
		// {results, errors} contract. Same class as validate()'s shape check,
		// applied to the envelope, degrading to the per-plugin error path the
		// transport failure above already uses.
		const errors = {};
		specs.forEach((s) => {
			errors[s.name] = "unexpected shape: expected the /all envelope";
		});
		return { results: {}, errors };
	}

	const results = {};
	const errors = {};
	for (const spec of specs) {
		if (!(spec.name in all)) {
			// Absent means the plugin has registered but not published
			// (scheduler cycle 0) -- a loading state, not an error. null is
			// what the component's `v-else-if="!payload"` branch expects.
			results[spec.name] = null;
			continue;
		}
		try {
			results[spec.name] = validate(all[spec.name], spec.spec);
		} catch (e) {
			errors[spec.name] = e.message;
		}
	}
	return { results, errors };
}
