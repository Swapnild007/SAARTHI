// Bundle only public application assets. Never copy backend, .env or test data.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'native-www');
const endpoint = process.env.SAARTHI_ANDROID_API_URL || '';
if (endpoint) {
  const url = new URL(endpoint);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/')
    throw Error('SAARTHI_ANDROID_API_URL must be an HTTPS origin without credentials or path.');
}
fs.mkdirSync(output, {recursive:true});
for (const name of ['index.html','manifest.webmanifest','styles','scripts','assets','appforge','config/runtime.json']) {
  const destination = path.join(output, name);
  fs.mkdirSync(path.dirname(destination), {recursive:true});
  fs.cpSync(path.join(root, name), destination, {recursive:true});
}
fs.writeFileSync(path.join(output, 'scripts/native-config.js'),
  'window.SaarthiNativeConfig=Object.freeze('+JSON.stringify({apiOrigin:endpoint ? new URL(endpoint).origin : ''})+');\n');
console.log('Android public assets prepared. API origin: '+(endpoint || 'unconfigured; offline utilities only'));
