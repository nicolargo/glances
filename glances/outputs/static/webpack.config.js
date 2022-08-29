const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");
const HtmlWebpackPlugin = require('html-webpack-plugin');
const PORT = process.env.PORT || 61209;

module.exports = (_, env) => {
    const isProd = env.mode === 'production';

    return {
        mode: isProd ? 'production' : 'development',
        entry: "./js/app.js",
        output: {
            path: path.join(__dirname, "public"),
            filename: "glances.js",
            publicPath: '/',
            clean: isProd
        },
        devtool: isProd ? false : 'eval-source-map',
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
                    test: /\.html$/,
                    use: [{
                        loader: "ngtemplate-loader",
                    }, {
                        loader: "html-loader",
                    }]
                }
            ],
        },
        plugins: [
            new CopyWebpackPlugin({
                patterns: [
                    { from: "./images/favicon.ico" }
                ]
            }),
            !isProd && new HtmlWebpackPlugin({
                template: './templates/index.html.tpl'
            }),
        ].filter(Boolean),
        devServer: {
            host: '0.0.0.0',
            port: PORT,
            hot: true,
            proxy: {
                '/api': {
                    target: 'http://0.0.0.0:61208'
                }
            }
        }

    };
};
