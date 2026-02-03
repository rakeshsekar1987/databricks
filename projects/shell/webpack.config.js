const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const share = mf.share;

/**
 * Shell (Host) Application - Webpack Module Federation Configuration
 * 
 * This is the main container application that dynamically loads remote modules.
 * Angular core libraries are shared as singletons for consistency across modules.
 * 
 * NOTE: Remotes are empty - we use loadRemoteModule for dynamic loading.
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
      
      // Remotes are empty - we load them dynamically via loadRemoteModule
      remotes: {},
      
      // Shared dependencies - Angular core as singletons
      // NOTE: zone.js is loaded as a polyfill and should NOT be shared
      shared: share({
        '@angular/core': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/common': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/common/http': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/router': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/forms': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/animations': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/platform-browser': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        '@angular/platform-browser-dynamic': { singleton: true, strictVersion: true, requiredVersion: 'auto' },
        'rxjs': { singleton: true, strictVersion: false, requiredVersion: 'auto' }
      })
    })
  ]
};
