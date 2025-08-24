(function () {
  try {
    const test = new URL('http://example.com');
    if (typeof test.protocol !== 'string') {
      throw new Error('protocol not implemented');
    }
  } catch (e) {
    global.URL = class URLPolyfill {
      constructor(url) {
        this.href = url;
        const match = String(url).match(/^([a-z0-9.+-]+:)/i);
        this.protocol = match ? match[1] : '';
      }
    };
  }
})();

const { registerRootComponent } = require('expo');
const App = require('./App').default;

registerRootComponent(App);
