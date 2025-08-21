const bridge = require('./src/extension');
const res = bridge.startBridge();
console.log('startBridge result:', res);
// keep process alive
setInterval(()=>{}, 1000);
