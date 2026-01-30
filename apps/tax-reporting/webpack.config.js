const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');
const webpack = require('webpack');
const deps = require('./package.json').dependencies;

/**
 * Production-ready Webpack configuration for Tax Reporting Module
 * Uses AG Grid v29.x
 */
module.exports = (env, argv) => {
  const isDevelopment = argv.mode === 'development';
  const isProduction = argv.mode === 'production';
  const port = process.env.PORT || 3004;

  return {
    entry: './src/index.ts',
    mode: isDevelopment ? 'development' : 'production',
    
    devtool: isDevelopment ? 'eval-source-map' : 'source-map',
    
    devServer: {
      port,
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
      // Use 'auto' for production to support different deployment URLs
      publicPath: isDevelopment ? `http://localhost:${port}/` : 'auto',
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
            },
          },
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.(png|jpg|jpeg|gif|svg|ico)$/,
          type: 'asset',
          parser: {
            dataUrlCondition: {
              maxSize: 8 * 1024,
            },
          },
        },
      ],
    },

    plugins: [
      new ModuleFederationPlugin({
        // Module name - used by host to identify this remote
        name: 'taxReporting',
        
        // Remote entry filename - loaded by host
        filename: 'remoteEntry.js',
        
        // Components exposed to host
        exposes: {
          './App': './src/App',
          './TaxReportingGrid': './src/components/TaxReportingGrid',
        },
        
        // Shared dependencies configuration
        shared: {
          // React is shared as singleton with host
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
          
          // Shared library is singleton
          '@platform/shared-library': {
            singleton: true,
            requiredVersion: '*',
          },
          
          // AG Grid v29 - NOT shared as singleton
          // This allows this module to use v29 while others use different versions
          'ag-grid-community': {
            singleton: false,
            requiredVersion: deps['ag-grid-community'],
            // Ensure this module bundles its own AG Grid
            eager: false,
          },
          'ag-grid-react': {
            singleton: false,
            requiredVersion: deps['ag-grid-react'],
            eager: false,
          },
          'ag-grid-enterprise': {
            singleton: false,
            requiredVersion: deps['ag-grid-enterprise'],
            eager: false,
          },
        },
      }),

      new HtmlWebpackPlugin({
        template: './public/index.html',
        title: 'Tax Reporting',
        // Minify in production
        minify: isProduction ? {
          removeComments: true,
          collapseWhitespace: true,
          removeRedundantAttributes: true,
        } : false,
      }),

      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(argv.mode),
        'process.env.AG_GRID_VERSION': JSON.stringify(deps['ag-grid-community']),
      }),
    ],

    optimization: {
      splitChunks: {
        chunks: 'async',
        cacheGroups: {
          // Bundle AG Grid separately for better caching
          agGrid: {
            test: /[\\/]node_modules[\\/]ag-grid/,
            name: 'ag-grid',
            chunks: 'all',
            priority: 30,
          },
        },
      },
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
    },
  };
};
