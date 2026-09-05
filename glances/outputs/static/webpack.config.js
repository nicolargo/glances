const webpack = require("webpack");
const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const TerserWebpackPlugin = require("terser-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");
const PORT = process.env.PORT || 61209;

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
		output: { ...outputBase, clean: false },
		optimization,
		devtool,
		performance,
		// createApp() from "vue" resolves to Vue's runtime-only build by
		// default (no template compiler), which silently sets render to a
		// no-op for a component that uses `template:` -- production mode
		// compiles out the dev warning, so the page just renders blank.
		// This alias is v5-only: v4's bundles must stay byte-identical.
		resolve: { alias: { vue: "vue/dist/vue.esm-bundler.js" } },
		// No CopyWebpackPlugin (favicon) or HtmlWebpackPlugin here: both
		// belong to the v4 build and would either duplicate work (favicon)
		// or overwrite v4's generated index.html in dev mode. The Vue
		// feature-flag defines are the only thing app_v5.js's dependency
		// graph (createApp from "vue") actually needs; vue-loader and its
		// plugin are added back by G9-2, which is the first change to
		// introduce a .vue component.
		plugins: [vueDefines],
	};

	return [v4Config, v5Config];
};
