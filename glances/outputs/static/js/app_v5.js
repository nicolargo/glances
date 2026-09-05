import { createApp } from "vue";

// Minimal v5 bootstrap. Its purpose is to prove the chain
// webpack build -> /static -> fetch -> Vue render against the v5 API.
// G9-2 replaces this body with the real application shell; it is a seed,
// not a parallel implementation.

// fetch() only rejects on a network failure, not on a 4xx/5xx response with
// a valid JSON body (e.g. FastAPI's {"detail": ...}) -- so callers must
// check response.ok themselves or a failed endpoint is silently treated as
// real data.
async function getJson(path) {
	const response = await fetch(path);
	if (!response.ok) {
		throw new Error(`${path}: HTTP ${response.status}`);
	}
	return response.json();
}

const app = createApp({
	data() {
		return {
			version: null,
			pluginCount: null,
			refresh: null,
			port: null,
			errors: [],
		};
	},
	async mounted() {
		// Each endpoint's outcome is independent (Promise.allSettled), so one
		// failing call doesn't discard the others -- the reader can tell
		// exactly which endpoint failed instead of the whole page going blank.
		const [all, args, config] = await Promise.allSettled([
			getJson("api/5/all"),
			getJson("api/5/args"),
			getJson("api/5/config"),
		]);

		if (all.status === "fulfilled") {
			this.pluginCount = Object.keys(all.value).length;
			this.version = all.value.version ? all.value.version.version : null;
		} else {
			this.errors.push(all.reason.message);
		}

		if (args.status === "fulfilled") {
			this.port = args.value.port;
		} else {
			this.errors.push(args.reason.message);
		}

		if (config.status === "fulfilled") {
			// The refresh rate lives in [global] refresh, not in the argument
			// namespace -- measured: v5's args carry no refresh key at all.
			this.refresh = config.value.global ? config.value.global.refresh : null;
		} else {
			this.errors.push(config.reason.message);
		}
	},
	template: `
		<main style="font-family: system-ui; padding: 2rem">
			<h1>Glances 5</h1>
			<ul v-if="errors.length">
				<li v-for="err in errors" :key="err">{{ err }}</li>
			</ul>
			<p>Version: {{ version ?? "…" }}</p>
			<p>Plugins served: {{ pluginCount ?? "…" }}</p>
			<p>Refresh: {{ refresh ?? "…" }} s</p>
			<p>Port: {{ port ?? "…" }}</p>
			<p>The v5 web interface is under construction. The REST API is live at
				<a href="api/5/all">/api/5/all</a>.</p>
		</main>
	`,
});

app.mount("#app");
