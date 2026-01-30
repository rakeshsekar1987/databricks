const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');
const deps = require('./package.json').dependencies;

module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';

  return {
    entry: './src/index.ts',
    mode: isDevelopment ? 'development' : 'production',
    devServer: {
      port: 3004,
      historyApiFallback: true,
      hot: true,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization',
      },
    },
    output: {
      publicPath: isDevelopment ? 'http://localhost:3004/' : 'auto',
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].[contenthash].js',
      clean: true,
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
    },
    module: {
      rules: [
        {
          test: /\.(ts|tsx|js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                '@babel/preset-env',
                ['@babel/preset-react', { runtime: 'automatic' }],
                '@babel/preset-typescript',
              ],
            },
          },
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ],
    },
    plugins: [
      new ModuleFederationPlugin({
        name: 'taxReporting',
        filename: 'remoteEntry.js',
        exposes: {
          './App': './src/App',
          './TaxReportingGrid': './src/components/TaxReportingGrid',
        },
        shared: {
          react: {
            singleton: true,
            requiredVersion: deps.react,
          },
          'react-dom': {
            singleton: true,
            requiredVersion: deps['react-dom'],
          },
          'react-router-dom': {
            singleton: true,
            requiredVersion: deps['react-router-dom'],
          },
          '@platform/shared-library': {
            singleton: true,
            requiredVersion: '*',
          },
          // AG Grid v29 - NOT shared as singleton
          // This module uses AG Grid v29.x
          'ag-grid-community': {
            singleton: false,
            requiredVersion: deps['ag-grid-community'],
          },
          'ag-grid-react': {
            singleton: false,
            requiredVersion: deps['ag-grid-react'],
          },
          'ag-grid-enterprise': {
            singleton: false,
            requiredVersion: deps['ag-grid-enterprise'],
          },
        },
      }),
      new HtmlWebpackPlugin({
        template: './public/index.html',
        title: 'Tax Reporting - Standalone',
      }),
    ],
    optimization: {
      splitChunks: {
        chunks: 'async',
      },
    },
  };
};
