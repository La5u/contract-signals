'use strict';
const fs = require('node:fs');
const { assess } = require('../indicator-evidence.js');
module.exports = { assess };
if (require.main === module) {
  try {
    if (process.argv.length !== 3) throw new Error('Usage: node tools/experimental-indicators.cjs evidence.json');
    const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
    console.log(JSON.stringify(Array.isArray(input) ? input.map(x => assess(x)) : assess(input), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
