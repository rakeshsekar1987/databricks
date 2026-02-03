const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const path = require('path');
const share = mf.share;

/**
 * Shell (Host) Application - Webpack Module Federation Configuration
 * 
 * This is the main container application that dynamically loads remote modules.
 * It shares Angular core libraries as singletons and loads Motif library as shared.
 */

const sharedMappings = new mf.SharedMappings();
sharedMappings.register(
  path.join(__dirname, '../../tsconfig.json'),
  ['@shared-lib']
);

module.exports = {
  output: {
    uniqueName: 'shell',
    publicPath: 'auto',
    scriptType: 'text/javascript'
  },
  optimization: {
    runtimeChunk: false
  },
  resolve: {
    alias: {
      ...sharedMappings.getAliases()
    }
  },
  experiments: {
    outputModule: true
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      filename: 'remoteEntry.js',
      
      // Remote modules configuration
      // In production, these URLs should come from environment configuration
      remotes: {
        'regReporting': 'regReporting@http://localhost:4201/remoteEntry.js',
        'financialReporting': 'financialReporting@http://localhost:4202/remoteEntry.js',
        'expenseReporting': 'expenseReporting@http://localhost:4203/remoteEntry.js',
        'taxReporting': 'taxReporting@http://localhost:4204/remoteEntry.js',
        'controlTower': 'controlTower@http://localhost:4205/remoteEntry.js'
      },
      
      // Shared dependencies - Angular core as singletons
      shared: share({
        '@angular/core': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        '@angular/common': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        '@angular/common/http': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        '@angular/router': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        '@angular/forms': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        '@angular/animations': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        '@angular/platform-browser': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        '@angular/platform-browser-dynamic': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto',
          eager: true
        },
        
        // Motif Library - Shared as singleton across all modules
        '@mfs/motif': {
          singleton: true,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        
        // RxJS shared
        'rxjs': {
          singleton: true,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        
        // Shared library
        '@shared-lib': {
          singleton: true,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        
        ...sharedMappings.getDescriptors()
      })
    }),
    sharedMappings.getPlugin()
  ]
};
