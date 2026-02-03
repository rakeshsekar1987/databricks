const { ModuleFederationPlugin } = require('webpack').container;
const mf = require('@angular-architects/module-federation/webpack');
const path = require('path');
const share = mf.share;

/**
 * Tax Reporting Module - Webpack Module Federation Configuration
 * 
 * Uses AG Grid v29.x for legacy compatibility.
 * Exposes routes and components for dynamic loading by the shell.
 */

const sharedMappings = new mf.SharedMappings();
sharedMappings.register(
  path.join(__dirname, '../../tsconfig.json'),
  ['@shared-lib']
);

module.exports = {
  output: {
    uniqueName: 'taxReporting',
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
      name: 'taxReporting',
      filename: 'remoteEntry.js',
      
      // Exposed modules
      exposes: {
        './routes': './projects/tax-reporting/src/app/app.routes.ts',
        './Module': './projects/tax-reporting/src/app/remote-entry/entry.component.ts'
      },
      
      // Shared dependencies
      shared: share({
        '@angular/core': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        '@angular/common': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        '@angular/common/http': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        '@angular/router': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
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
          requiredVersion: 'auto'
        },
        '@angular/platform-browser-dynamic': {
          singleton: true,
          strictVersion: true,
          requiredVersion: 'auto'
        },
        
        // AG Grid - NOT singleton, allows different versions per module
        'ag-grid-community': {
          singleton: false,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        'ag-grid-angular': {
          singleton: false,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        
        'rxjs': {
          singleton: true,
          strictVersion: false,
          requiredVersion: 'auto'
        },
        
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
