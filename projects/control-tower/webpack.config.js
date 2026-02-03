const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const share = mf.share;

/**
 * Control Tower Module - Webpack Module Federation Configuration
 * Uses AG Grid v31.x (Community Edition)
 */

module.exports = {
  output: {
    uniqueName: 'controlTower',
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
      name: 'controlTower',
      filename: 'remoteEntry.js',
      
      exposes: {
        './routes': './projects/control-tower/src/app/app.routes.ts',
        './Module': './projects/control-tower/src/app/remote-entry/entry.component.ts'
      },
      
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
        'ag-grid-community': { singleton: false, strictVersion: false, requiredVersion: 'auto' },
        'ag-grid-angular': { singleton: false, strictVersion: false, requiredVersion: 'auto' }
      })
    })
  ]
};
