
const webpack = require("webpack");
const path = require("path");

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = {
    mode: 'development',
    entry: "./js/app.js",
    output: {
        path: path.join(__dirname, "public"),
        filename: "glances.js",
        sourceMapFilename: "glances.map.js",
    },
    optimization: {
        minimize: false,
    },
    devtool: "source-map",
    module: {
        rules: [
            {
                test: /\.scss$/,
                use: [{
                    loader: "style-loader",
                }, {
                    loader: "css-loader",
                }, {
                    loader: "sass-loader",
                }]
            },
            {
                test: /\.less$/,
                use: [{
                    loader: "style-loader",
                }, {
                    loader: "css-loader",
                }, {
                    loader: "less-loader",
                }]
            },
            {
                test: /\.css$/,
                use: [{
                    loader: "style-loader",
                }, {
                    loader: "css-loader",
                }]
            },
            {
                test: /\.html/,
                use: [{
                    loader: "ngtemplate-loader",
                }, {
                    loader: "html-loader",
                }]
            }
        ],
    },
    plugins: [
        new CleanWebpackPlugin(),
        new CopyWebpackPlugin({
            patterns: [
                { from: "./images/favicon.ico" }
            ]
        }),
    ]
};
