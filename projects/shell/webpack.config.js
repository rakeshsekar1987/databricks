const { ModuleFederationPlugin } = require('webpack').container;

/**
 * Shell (Host) Application - Webpack Module Federation Configuration
 */

module.exports = {
  output: {
    uniqueName: 'shell',
    publicPath: 'auto'
  },
  optimization: {
    runtimeChunk: false
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      filename: 'remoteEntry.js',
      remotes: {},
      shared: {
        '@angular/core': { singleton: true, strictVersion: false },
        '@angular/common': { singleton: true, strictVersion: false },
        '@angular/common/http': { singleton: true, strictVersion: false },
        '@angular/router': { singleton: true, strictVersion: false },
        '@angular/forms': { singleton: true, strictVersion: false },
        '@angular/animations': { singleton: true, strictVersion: false },
        '@angular/platform-browser': { singleton: true, strictVersion: false },
        '@angular/platform-browser-dynamic': { singleton: true, strictVersion: false },
        'rxjs': { singleton: true, strictVersion: false }
      }
    })
  ]
};
