const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const path = require('path');
const share = mf.share;

/**
 * Financial Reporting Module - Webpack Module Federation Configuration
 * Uses AG Grid v30.x
 */
const sharedMappings = new mf.SharedMappings();
sharedMappings.register(
  path.join(__dirname, '../../tsconfig.json'),
  ['@shared-lib']
);

module.exports = {
  output: {
    uniqueName: 'financialReporting',
    publicPath: 'auto',
    scriptType: 'text/javascript'
  },
  optimization: { runtimeChunk: false },
  resolve: { alias: { ...sharedMappings.getAliases() } },
  experiments: { outputModule: true },
  plugins: [
    new ModuleFederationPlugin({
      name: 'financialReporting',
      filename: 'remoteEntry.js',
      exposes: {
        './routes': './projects/financial-reporting/src/app/app.routes.ts',
        './Module': './projects/financial-reporting/src/app/remote-entry/entry.component.ts'
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
        '@mfs/motif': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        'ag-grid-community': { singleton: false, strictVersion: false, requiredVersion: '^30.2.0' },
        'ag-grid-angular': { singleton: false, strictVersion: false, requiredVersion: '^30.2.0' },
        'ag-grid-enterprise': { singleton: false, strictVersion: false, requiredVersion: '^30.2.0' },
        'rxjs': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        '@shared-lib': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        ...sharedMappings.getDescriptors()
      })
    }),
    sharedMappings.getPlugin()
  ]
};
