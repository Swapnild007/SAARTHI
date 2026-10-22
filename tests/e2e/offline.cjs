const assert=require('node:assert/strict');require('../../scripts/utilities.js');
for(const [input,value] of [['(12 + 8) * 3',60],['15% of 200',30],['-2 * -3',6]])assert.equal(SaarthiOffline.calculate(input).value,value);
for(const input of ['alert(1)','1 / 0','(1+2','9 ** 99999999'])assert.throws(()=>SaarthiOffline.calculate(input));
assert.equal(SaarthiOffline.run('calculator').intent.name,'calculate');assert(!('system.time' in SaarthiOffline.run('calculator').tool_results));assert.equal(SaarthiOffline.run('tell me a story').execution,'offline-unavailable');console.log('PASS: offline arithmetic, bounds, routing and honest cloud fallback');
