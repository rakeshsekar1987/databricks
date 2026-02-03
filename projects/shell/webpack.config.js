const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const share = mf.share;

/**
 * Shell (Host) Application - Webpack Module Federation Configuration
 * 
 * This is the main container application that dynamically loads remote modules.
 * Angular core libraries are shared as singletons for consistency across modules.
 */

module.exports = {
  output: {
    uniqueName: 'shell',
    publicPath: 'auto',
    scriptType: 'text/javascript'
  },
  optimization: {
    runtimeChunk: false
  },
  experiments: {
    outputModule: true
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      filename: 'remoteEntry.js',
      
      // Remote modules configuration
      remotes: {
        'regReporting': 'regReporting@http://localhost:4201/remoteEntry.js',
        'financialReporting': 'financialReporting@http://localhost:4202/remoteEntry.js',
        'expenseReporting': 'expenseReporting@http://localhost:4203/remoteEntry.js',
        'taxReporting': 'taxReporting@http://localhost:4204/remoteEntry.js',
        'controlTower': 'controlTower@http://localhost:4205/remoteEntry.js'
      },
      
      // Shared dependencies - Angular core as singletons
      shared: share({
        '@angular/core': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/common': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/common/http': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/router': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/forms': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/animations': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/platform-browser': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/platform-browser-dynamic': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        'rxjs': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        'zone.js': { singleton: true, strictVersion: false, requiredVersion: 'auto' }
      })
    })
  ]
};
