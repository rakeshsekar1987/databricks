const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');
const deps = require('./package.json').dependencies;

// Module Registry - Configure remote module URLs
// In production, these would come from environment variables or a configuration service
const getRemoteUrl = (moduleName, port) => {
  const isDev = process.env.NODE_ENV !== 'production';
  const baseUrl = isDev
    ? `http://localhost:${port}`
    : process.env[`${moduleName.toUpperCase()}_URL`] || `https://cdn.example.com/${moduleName}`;
  return `${moduleName}@${baseUrl}/remoteEntry.js`;
};

module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';

  return {
    entry: './src/index.ts',
    mode: isDevelopment ? 'development' : 'production',
    devServer: {
      port: 3000,
      historyApiFallback: true,
      hot: true,
      headers: {
        'Access-Control-Allow-Origin': '*',
      },
    },
    output: {
      publicPath: isDevelopment ? 'http://localhost:3000/' : '/',
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
        name: 'shell',
        // Shell is the HOST - it consumes remote modules
        remotes: {
          // Remote modules will be loaded dynamically in production
          // These URLs would come from environment or configuration service
          regReporting: getRemoteUrl('regReporting', 3001),
          financialReporting: getRemoteUrl('financialReporting', 3002),
          expenseReporting: getRemoteUrl('expenseReporting', 3003),
          taxReporting: getRemoteUrl('taxReporting', 3004),
          controlTower: getRemoteUrl('controlTower', 3005),
        },
        shared: {
          // React is shared as singleton - same version across all modules
          react: {
            singleton: true,
            requiredVersion: deps.react,
            eager: true,
          },
          'react-dom': {
            singleton: true,
            requiredVersion: deps['react-dom'],
            eager: true,
          },
          'react-router-dom': {
            singleton: true,
            requiredVersion: deps['react-router-dom'],
          },
          // Shared library is shared across all modules
          '@platform/shared-library': {
            singleton: true,
            requiredVersion: '*',
          },
          // NOTE: ag-grid is NOT shared as singleton
          // Each module can have its own version
        },
      }),
      new HtmlWebpackPlugin({
        template: './public/index.html',
        title: 'UI Platform - Module Federation',
      }),
    ],
    optimization: {
      splitChunks: {
        chunks: 'all',
      },
    },
  };
};
