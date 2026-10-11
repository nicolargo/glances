const webpack = require("webpack");
const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const TerserWebpackPlugin = require("terser-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");
// Number(): the environment only holds strings.
const PORT = Number(process.env.PORT) || 61209;

module.exports = (_, env) => {
	const isProd = env.mode === "production";

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

	const config = {
		name: "glances",
		mode,
		entry: {
			glances: "./js/app.js",
			// The browser page (P3-6), served at /browser by `-s --browser`.
			browser: "./js/browser_app.js",
		},
		// index.html loads the bundle as "static/glances.js" -- the path
		// the Python server mounts it on. In dev the bundle lives in the dev
		// server's memory, so it has to be published under the same prefix or
		// the served page 404s on its only <script>. Production is untouched.
		output: { ...outputBase, clean: true, publicPath: isProd ? outputBase.publicPath : "/static/" },
		optimization,
		devtool,
		performance,
		// No `resolve.alias` to vue/dist/vue.esm-bundler.js: every v5
		// component is a single-file component compiled by vue-loader at
		// build time, so no `template:` string survives into the bundle and
		// Vue's runtime-only build (the default resolution of "vue") is
		// enough. The full build shipped a template compiler the bundle never
		// called, in a single module terser cannot tree-shake: dropping the
		// alias took glances.js from 190 KB to 77 KB.
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
			new CopyWebpackPlugin({
				patterns: [{ from: "./images/favicon.ico" }],
			}),
			// Dev-only: without it the v5 dev server has no
			// index.html of its own to serve at `/`. The dev server keeps it
			// in memory, so public/ is untouched.
			!isProd &&
				new HtmlWebpackPlugin({
					template: "./templates/index.html",
					inject: false,
				}),
			new VueLoaderPlugin(),
		].filter(Boolean),
		devServer: {
			client: { overlay: false },
			host: "0.0.0.0",
			port: PORT,
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

	return config;
};
