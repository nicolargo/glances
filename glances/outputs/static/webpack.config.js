 
const webpack = require('webpack');
const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require('html-webpack-plugin');
const TerserWebpackPlugin = require('terser-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');
const PORT = process.env.PORT || 61210;

module.exports = (_, env) => {
    const isProd = env.mode === 'production';

    return {
        mode: isProd ? 'production' : 'development',
        entry: {
            glances: "./js/app.js",
            browser: "./js/browser.js"
        },
        output: {
            path: path.join(__dirname, "public"),
            filename: "static/[name].js",
            publicPath: '/',
            clean: true
        },
        devtool: isProd ? false : 'eval-source-map',
        module: {
            rules: [
                {
                    test: /\.vue$/i,
                    loader: 'vue-loader'
                },
                {
                    test: /\.scss$/i,
                    use: [{
                        loader: "style-loader",
                    }, {
                        loader: "css-loader",
                    }, {
                        loader: "sass-loader",
                    }]
                },
                {
                    test: /\.css$/i,
                    use: [{
                        loader: "style-loader",
                    }, {
                        loader: "css-loader",
                    }]
                }
            ],
        },
        plugins: [
            new webpack.DefinePlugin({
                __VUE_OPTIONS_API__: true,
                __VUE_PROD_DEVTOOLS__: false,
                __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false
            }),
            new CopyWebpackPlugin({
                patterns: [
                    { from: "./images/favicon.ico" }
                ]
            }),
            !isProd && new HtmlWebpackPlugin({
                template: './templates/index.html',
                inject: false
            }),
            isProd && new TerserWebpackPlugin({ extractComments: false }),
            new VueLoaderPlugin()
        ].filter(Boolean),
        devServer: {
            client: {
                overlay: false
            },
            host: '0.0.0.0',
            port: PORT,
            hot: true,
            proxy: [
                {
                    context: ['/api'],
                    target: 'http://0.0.0.0:61208'
                }
            ]
        }

    };
};
