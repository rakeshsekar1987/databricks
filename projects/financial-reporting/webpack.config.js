const { ModuleFederationPlugin } = require('webpack').container;

/**
 * Financial Reporting Module - Webpack Module Federation Configuration
 */

module.exports = {
  output: {
    uniqueName: 'financialReporting',
    publicPath: 'auto'
  },
  optimization: {
    runtimeChunk: false
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'financialReporting',
      filename: 'remoteEntry.js',
      exposes: {
        './routes': './projects/financial-reporting/src/app/app.routes.ts',
        './Module': './projects/financial-reporting/src/app/remote-entry/entry.component.ts'
      },
      shared: {
        '@angular/core': { singleton: true, strictVersion: false },
        '@angular/common': { singleton: true, strictVersion: false },
        '@angular/common/http': { singleton: true, strictVersion: false },
        '@angular/router': { singleton: true, strictVersion: false },
        '@angular/forms': { singleton: true, strictVersion: false },
        '@angular/animations': { singleton: true, strictVersion: false },
        '@angular/platform-browser': { singleton: true, strictVersion: false },
        '@angular/platform-browser-dynamic': { singleton: true, strictVersion: false },
        'rxjs': { singleton: true, strictVersion: false },
        'ag-grid-community': { singleton: false, strictVersion: false },
        'ag-grid-angular': { singleton: false, strictVersion: false }
      }
    })
  ]
};
