// Glances v5 WebUI — the only module that talks to the v5 REST API.
//
// Three things components must not each reinvent:
//
// 1. `fetch` does NOT reject on 4xx/5xx. Only a network failure rejects, so a
//    500 carrying a JSON error body parses cleanly and looks like data.
// 2. Nor does a status check catch a 200 whose BODY is the wrong shape
//    (FastAPI's `{"detail": ...}`). An early diagnostic page reported a
//    plausible, wrong plugin count for exactly this reason. Hence `validate`.
// 3. Endpoint outcomes must be independent: one plugin's failure must not
//    blank the page.

export const DEFAULT_REFRESH_SECONDS = 2;
export const DEFAULT_THEME = "dark";
export const DEFAULT_API_DOC = true;
const VALID_THEMES = new Set(["dark", "light"]);
const TRUE_STRINGS = new Set(["1", "true", "yes", "on"]);
const FALSE_STRINGS = new Set(["0", "false", "no", "off"]);

export async function getJson(path) {
	const response = await fetch(path);
	if (!response.ok) {
		throw new Error(`${path}: HTTP ${response.status}`);
	}
	return response.json();
}

export function validate(payload, spec) {
	// `200 null` means the plugin has registered but has not published yet
	// (scheduler cycle 0) -- the route contract. A loading state, not a
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
	// fetch. NOT /api/5/args: measured -- the v5 argument namespace
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
		return {
			refreshSeconds: DEFAULT_REFRESH_SECONDS,
			theme: DEFAULT_THEME,
			maxProcessesDisplay: null,
			apiDoc: DEFAULT_API_DOC,
		};
	}
	const refresh = config && config.global && config.global.refresh;
	const seconds = Number(refresh);
	const refreshSeconds = Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_REFRESH_SECONDS;

	// A typo or unrecognised value must not be written through to
	// data-theme -- fall back to the same default `[outputs] theme` itself
	// uses (glances_curses_v5.py:226) rather than shipping an unstyled page.
	const rawTheme = config && config.outputs && config.outputs.theme;
	const theme = VALID_THEMES.has(rawTheme) ? rawTheme : DEFAULT_THEME;

	// `[outputs] max_processes_display` -- v4 parity (plugin-processlist.vue:590
	// reads it and slices IN THE BROWSER; the server-side read in
	// glances_restful_api.py assigns a local and only logs it, dead code not
	// reproduced here). Resolved once, here, alongside refresh/theme -- not
	// fetched a second time by PluginProcesslist.vue itself -- and handed
	// down through AppShell's `provide()`, the same
	// mechanism `serverPlugins` already uses for a value only ONE plugin reads.
	// `null` means "no cap": absent key, or a value that does not parse to a
	// positive integer.
	const rawMaxProcesses = config && config.outputs && config.outputs.max_processes_display;
	const maxProcessesN = Number(rawMaxProcesses);
	const maxProcessesDisplay = Number.isFinite(maxProcessesN) && maxProcessesN > 0 ? Math.trunc(maxProcessesN) : null;

	// `[outputs] api_doc` -- the SAME gate webserver_v5.build_app() uses to
	// decide whether FastAPI mounts /docs at all. Read here so the footer can
	// link the Swagger UI only when it exists: a link to a 404 is worse than
	// no link. Defaults to true, as GlancesConfigV5.DEFAULTS does.
	const apiDoc = coerceBool(config && config.outputs && config.outputs.api_doc, DEFAULT_API_DOC);

	return { refreshSeconds, theme, maxProcessesDisplay, apiDoc };
}

function coerceBool(raw, fallback) {
	// /api/5/config serves the MERGED config, whose layers disagree on type:
	// GlancesConfigV5.DEFAULTS holds a real boolean, the CLI overlay writes
	// one too, but a value read from glances.conf arrives as the raw string
	// "false". The accepted spellings are GlancesConfigV5._coerce_bool()'s.
	if (typeof raw === "boolean") return raw;
	if (typeof raw === "string") {
		const value = raw.trim().toLowerCase();
		if (TRUE_STRINGS.has(value)) return true;
		if (FALSE_STRINGS.has(value)) return false;
	}
	return fallback;
}

export async function resolveVersion() {
	// /status, not /api/5/... -- the health probe is where v4 already serves
	// the release (`/api/4/status`), and v5's carries it as `glances_version`
	// next to the API version. Read once per page load, like the schema and
	// the arguments.
	//
	// null on any failure: the footer then names no version rather than
	// showing an error. Nothing else on the page depends on it.
	try {
		const status = await getJson("status");
		return status && typeof status.glances_version === "string" ? status.glances_version : null;
	} catch {
		return null;
	}
}

let argsCache = null;

export async function resolveArgs() {
	// The server's CLI arguments -- `--meangpu` and `--fahrenheit` today.
	// They cannot change while the server runs, so this is fetched once per
	// page load and cached, exactly like the schema in labels.js.
	//
	// NOT merged into resolveConfig(): that reads /api/5/config, and the two
	// namespaces are genuinely different (the argument namespace carries no
	// `refresh` key at all).
	if (argsCache) return argsCache;
	try {
		argsCache = await getJson("api/5/args");
	} catch {
		// A UI that cannot read the arguments renders in Celsius and lets the
		// card count decide gpu's layout. That is a degraded view, not a
		// broken one -- never a reason to blank the page.
		argsCache = {};
	}
	return argsCache;
}

export async function resolvePluginNames() {
	// /api/5/pluginslist: the plugins the server actually instantiated. Read
	// once per page load. When runtime plugin toggling lands (#3548), a plugin
	// enabled after the tab opened appears on the next reload -- a known
	// limitation, not a bug to fix with a per-tick fetch.
	//
	// null, never [], on failure: an empty list would hide every plugin, while
	// null tells visiblePlugins() to fall back to the whole registry.
	try {
		const names = await getJson("api/5/pluginslist");
		return Array.isArray(names) ? names : null;
	} catch {
		return null;
	}
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
