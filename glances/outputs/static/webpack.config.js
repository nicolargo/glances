
const webpack = require("webpack");
const path = require("path");

const CleanWebpackPlugin = require("clean-webpack-plugin");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = {
    entry: "./js/app.js",
    output: {
        path: path.join(__dirname, "public"),
        filename: "glances.js",
        sourceMapFilename: "glances.map.js",
    },
    devtool: "#source-map",
    module: {
        loaders: [
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
                loader: "style-loader!css-loader",
            },
            {
                test: /\.(png|jpg|gif|svg|ttf|woff|woff2|eot)$/,
                loader: "url-loader",
                options: {
                    limit: 10000,
                }
            },
            {
                test: /\.html/,
                loader: "ngtemplate-loader!html-loader"
            },
            {
                test: require.resolve("angular"),
                loader: "exports-loader?window.angular"
            },
        ],
    },
    plugins: [
        new CleanWebpackPlugin("./public/*.*"),
        new CopyWebpackPlugin([
            { from: "./images/favicon.ico" }
        ]),
    ]
};