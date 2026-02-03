const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const path = require('path');
const share = mf.share;

/**
 * Expense Reporting Module - AG Grid v31.x
 */
const sharedMappings = new mf.SharedMappings();
sharedMappings.register(path.join(__dirname, '../../tsconfig.json'), ['@shared-lib']);

module.exports = {
  output: { uniqueName: 'expenseReporting', publicPath: 'auto', scriptType: 'text/javascript' },
  optimization: { runtimeChunk: false },
  resolve: { alias: { ...sharedMappings.getAliases() } },
  experiments: { outputModule: true },
  plugins: [
    new ModuleFederationPlugin({
      name: 'expenseReporting',
      filename: 'remoteEntry.js',
      exposes: {
        './routes': './projects/expense-reporting/src/app/app.routes.ts',
        './Module': './projects/expense-reporting/src/app/remote-entry/entry.component.ts'
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
        'ag-grid-community': { singleton: false, strictVersion: false, requiredVersion: '^31.0.0' },
        'ag-grid-angular': { singleton: false, strictVersion: false, requiredVersion: '^31.0.0' },
        'rxjs': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        '@shared-lib': { singleton: true, strictVersion: false, requiredVersion: 'auto' },
        ...sharedMappings.getDescriptors()
      })
    }),
    sharedMappings.getPlugin()
  ]
};
