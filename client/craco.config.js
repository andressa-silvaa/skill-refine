const fs = require('fs');
const path = require('path');
const evalSourceMapMiddleware = require('react-dev-utils/evalSourceMapMiddleware');
const noopServiceWorkerMiddleware = require('react-dev-utils/noopServiceWorkerMiddleware');
const redirectServedPath = require('react-dev-utils/redirectServedPathMiddleware');
const paths = require('react-scripts/config/paths');

module.exports = {
  devServer: (devServerConfig) => {
    delete devServerConfig.onBeforeSetupMiddleware;
    delete devServerConfig.onAfterSetupMiddleware;

    const existingSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      devServer.app.use(evalSourceMapMiddleware(devServer));
      if (fs.existsSync(paths.proxySetup)) {
        require(paths.proxySetup)(devServer.app);
      }

      let m = middlewares;
      if (typeof existingSetupMiddlewares === 'function') {
        m = existingSetupMiddlewares(middlewares, devServer);
      }

      m.push(
        {
          name: 'redirect-served-path',
          middleware: redirectServedPath(paths.publicUrlOrPath),
        },
        {
          name: 'noop-service-worker',
          middleware: noopServiceWorkerMiddleware(paths.publicUrlOrPath),
        }
      );

      return m;
    };

    return devServerConfig;
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  jest: {
    configure: (jestConfig) => {
      jestConfig.moduleNameMapper = {
        ...(jestConfig.moduleNameMapper ?? {}),
        '^@/(.*)$': '<rootDir>/src/$1',
      };
      return jestConfig;
    },
  },
};


