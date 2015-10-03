'use strict';

exports.config = {
  watcher: {
    usePolling: true
  },
  modules: {
    definition: false,
    wrapper: false
  },
  files: {
    javascripts: {
      joinTo: {
        'js/scripts.js': /^app/,
        'js/vendors.js': /^bower_components/
      }
    },
    stylesheets: {
      joinTo: {
        'styles/main.css': /^app/,
        'styles/vendors.css': /^bower_components/
      }
    }
  },
  plugins: {
      assetsmanager: {
        copyTo: {
          'images': ['/app/images/*'],
          'fonts' : ['bower_components/font-awesome/fonts/*']
        }
      }
  }
};
