const webpack = require("webpack");
const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const TerserWebpackPlugin = require("terser-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");
// Number(): the environment only holds strings, and `PORT + 1` below would
// concatenate ("8080" + 1 -> "80801").
const PORT = Number(process.env.PORT) || 61209;

module.exports = (_, env) => {
	const isProd = env.mode === "production";

	// Shared across both compilations: the v4 config and the v5 config each
	// write "[name].js" into the same public/ directory but must not share a
	// module-id space -- see the two `entry` blocks below.
	const mode = isProd ? "production" : "development";
	const devtool = isProd ? false : "eval-source-map";
	const optimization = {
		minimizer: [new TerserWebpackPlugin({ extractComments: false })],
	};
	const performance = { hints: false };
	const outputBase = {
		path: path.join(__dirname, "public"),
		filename: "[name].js",
		publicPath: "/",
	};
	const vueDefines = new webpack.DefinePlugin({
		__VUE_OPTIONS_API__: true,
		__VUE_PROD_DEVTOOLS__: false,
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	});

	const v4Config = {
		name: "v4",
		mode,
		entry: {
			glances: "./js/app.js",
			browser: "./js/browser.js",
		},
		// This compilation owns the directory clean-up. The v5 compilation
		// below depends on it finishing first and must NOT also clean, or
		// the two compilers race to delete each other's freshly emitted
		// output.
		output: { ...outputBase, clean: true },
		optimization,
		devtool,
		performance,
		module: {
			rules: [
				{
					test: /\.vue$/i,
					loader: "vue-loader",
				},
				{
					test: /\.scss$/i,
					use: [
						{
							loader: "style-loader",
						},
						{
							loader: "css-loader",
						},
						{
							loader: "sass-loader",
							options: {
								sassOptions: {
									silenceDeprecations: ["import", "global-builtin", "color-functions", "if-function"],
								},
							},
						},
					],
				},
				{
					test: /\.css$/i,
					use: [
						{
							loader: "style-loader",
						},
						{
							loader: "css-loader",
						},
					],
				},
			],
		},
		plugins: [
			vueDefines,
			new CopyWebpackPlugin({
				patterns: [{ from: "./images/favicon.ico" }],
			}),
			!isProd &&
				new HtmlWebpackPlugin({
					template: "./templates/index.html",
					inject: false,
				}),
			new VueLoaderPlugin(),
		].filter(Boolean),
		devServer: {
			client: {
				overlay: false,
			},
			host: "0.0.0.0",
			port: PORT,
			hot: true,
			proxy: [
				{
					context: ["/api"],
					target: "http://0.0.0.0:61208",
				},
			],
		},
	};

	const v5Config = {
		name: "v5",
		// Forces webpack to finish the v4 compilation (and its directory
		// clean) before this one starts, so the two never race over
		// public/.
		dependencies: ["v4"],
		mode,
		entry: {
			glances5: "./js/app_v5.js",
		},
		// index_v5.html loads the bundle as "static/glances5.js" -- the path
		// the Python server mounts it on. In dev the bundle lives in the dev
		// server's memory, so it has to be published under the same prefix or
		// the served page 404s on its only <script>. Production is untouched.
		output: { ...outputBase, clean: false, publicPath: isProd ? outputBase.publicPath : "/static/" },
		optimization,
		devtool,
		performance,
		// No `resolve.alias` to vue/dist/vue.esm-bundler.js: every v5
		// component is a single-file component compiled by vue-loader at
		// build time, so no `template:` string survives into the bundle and
		// Vue's runtime-only build (the default resolution of "vue") is
		// enough. The full build shipped a template compiler the bundle never
		// called, in a single module terser cannot tree-shake: dropping the
		// alias took glances5.js from 190 KB to 77 KB.
		// No CopyWebpackPlugin (favicon) here: it belongs to the v4 build
		// and would duplicate the work. The Vue feature-flag defines are the
		// only thing app_v5.js's dependency graph (createApp from "vue")
		// actually needs; vue-loader and its plugin are added back by G9-2,
		// which is the first change to introduce a .vue component.
		module: {
			rules: [
				{
					test: /\.vue$/i,
					loader: "vue-loader",
				},
				{
					test: /\.css$/i,
					use: [{ loader: "style-loader" }, { loader: "css-loader" }],
				},
			],
		},
		// vue-loader and its plugin come back with this group: G9-1 removed
		// them as dead config because no .vue file existed yet.
		plugins: [
			vueDefines,
			// Dev-only, like v4's: without it the v5 dev server has no
			// index.html of its own to serve at `/`. The dev server keeps it
			// in memory, so public/ is untouched.
			!isProd &&
				new HtmlWebpackPlugin({
					template: "./templates/index_v5.html",
					inject: false,
				}),
			new VueLoaderPlugin(),
		].filter(Boolean),
		// G9-1 left `npm start` serving v4 only: webpack-dev-server picks the
		// config carrying `devServer`, which was v4Config's. Without this,
		// G9-3..N develop 32 components with no hot reload -- a tax paid 32
		// times. A distinct port lets both dev servers run side by side.
		devServer: {
			client: { overlay: false },
			host: "0.0.0.0",
			port: PORT + 1,
			hot: true,
			// Without this every fetch("api/5/...") from the dev server hits
			// the dev server itself and 404s. Array form: the object form
			// webpack-dev-server 4 took is silently ignored by 5.
			proxy: [
				{
					context: ["/api"],
					target: "http://0.0.0.0:61208",
				},
			],
		},
	};

	return [v4Config, v5Config];
};
