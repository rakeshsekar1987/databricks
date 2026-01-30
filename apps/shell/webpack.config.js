const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');
const webpack = require('webpack');
const deps = require('./package.json').dependencies;

// Load environment variables
require('dotenv').config({ path: '.env.local' });
require('dotenv').config();

/**
 * Production-ready Webpack configuration for Shell (Host) application
 */
module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';
  const isProduction = argv.mode === 'production';

  // Remote module URLs - use environment variables in production
  const getRemoteUrl = (moduleName, devPort) => {
    if (isDevelopment) {
      return `${moduleName}@http://localhost:${devPort}/remoteEntry.js`;
    }
    // In production, use environment variables or CDN URLs
    const envKey = `${moduleName.toUpperCase().replace(/-/g, '_')}_URL`;
    const baseUrl = process.env[envKey] || `https://cdn.example.com/${moduleName}`;
    return `${moduleName}@${baseUrl}/remoteEntry.js`;
  };

  // Only include remotes if not using dynamic loading
  const remotes = process.env.ENABLE_DYNAMIC_REMOTES === 'true' ? {} : {
    regReporting: getRemoteUrl('regReporting', 3001),
    financialReporting: getRemoteUrl('financialReporting', 3002),
    expenseReporting: getRemoteUrl('expenseReporting', 3003),
    taxReporting: getRemoteUrl('taxReporting', 3004),
    controlTower: getRemoteUrl('controlTower', 3005),
  };

  return {
    entry: './src/index.ts',
    mode: isDevelopment ? 'development' : 'production',
    
    devtool: isDevelopment ? 'eval-source-map' : 'source-map',
    
    devServer: {
      port: process.env.PORT || 3000,
      historyApiFallback: true,
      hot: true,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization',
      },
      client: {
        overlay: {
          errors: true,
          warnings: false,
        },
      },
    },

    output: {
      publicPath: isDevelopment ? 'http://localhost:3000/' : 'auto',
      path: path.resolve(__dirname, 'dist'),
      filename: isProduction ? '[name].[contenthash:8].js' : '[name].js',
      chunkFilename: isProduction ? '[name].[contenthash:8].chunk.js' : '[name].chunk.js',
      clean: true,
    },

    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },

    module: {
      rules: [
        {
          test: /\.(ts|tsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', { 
                  targets: { browsers: ['last 2 versions', '> 1%'] },
                  useBuiltIns: 'usage',
                  corejs: 3,
                }],
                ['@babel/preset-react', { runtime: 'automatic' }],
                '@babel/preset-typescript',
              ],
              plugins: isProduction ? [] : ['react-refresh/babel'],
            },
          },
        },
        {
          test: /\.css$/,
          use: [
            'style-loader',
            {
              loader: 'css-loader',
              options: {
                importLoaders: 1,
                modules: {
                  auto: true,
                  localIdentName: isDevelopment 
                    ? '[name]__[local]--[hash:base64:5]' 
                    : '[hash:base64:8]',
                },
              },
            },
          ],
        },
        {
          test: /\.(png|jpg|jpeg|gif|svg|ico)$/,
          type: 'asset',
          parser: {
            dataUrlCondition: {
              maxSize: 8 * 1024, // 8kb
            },
          },
        },
        {
          test: /\.(woff|woff2|eot|ttf|otf)$/,
          type: 'asset/resource',
        },
      ],
    },

    plugins: [
      new ModuleFederationPlugin({
        name: 'shell',
        remotes,
        shared: {
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
          '@platform/shared-library': {
            singleton: true,
            requiredVersion: '*',
          },
        },
      }),

      new HtmlWebpackPlugin({
        template: './public/index.html',
        title: 'UI Platform',
        minify: isProduction ? {
          removeComments: true,
          collapseWhitespace: true,
          removeRedundantAttributes: true,
          useShortDoctype: true,
          removeEmptyAttributes: true,
          removeStyleLinkTypeAttributes: true,
          keepClosingSlash: true,
          minifyJS: true,
          minifyCSS: true,
          minifyURLs: true,
        } : false,
      }),

      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(argv.mode),
        'process.env.MODULE_REGISTRY_URL': JSON.stringify(process.env.MODULE_REGISTRY_URL || ''),
        'process.env.ENABLE_DYNAMIC_REMOTES': JSON.stringify(process.env.ENABLE_DYNAMIC_REMOTES || 'false'),
        'process.env.API_BASE_URL': JSON.stringify(process.env.API_BASE_URL || ''),
      }),

      // Hot module replacement for development
      isDevelopment && new (require('@pmmmwh/react-refresh-webpack-plugin'))(),
    ].filter(Boolean),

    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
            priority: 20,
          },
          common: {
            minChunks: 2,
            priority: 10,
            reuseExistingChunk: true,
          },
        },
      },
      runtimeChunk: 'single',
      minimize: isProduction,
    },

    performance: {
      hints: isProduction ? 'warning' : false,
      maxEntrypointSize: 512000,
      maxAssetSize: 512000,
    },

    stats: {
      colors: true,
      modules: false,
      children: false,
      chunks: false,
      chunkModules: false,
    },
  };
};
