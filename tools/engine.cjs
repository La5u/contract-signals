// The scoring engine for Node tools and tests, as index.html loads it: its <script data-engine> files in
// page order (scoring.js ... views.js; no DOM). The explorer page itself is script.js, loaded after them.
// A directory without scoring.js is a checkout from before the split (2026-10-20): its engine is script.js.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function engineFiles(dir = root) {
  if (!fs.existsSync(path.join(dir, 'scoring.js'))) return ['script.js'];
  const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
  const files = [...html.matchAll(/<script src="([^"]+)" data-engine\b/g)].map(m => m[1]);
  if (!files.length || files[0] !== 'scoring.js') throw new Error('index.html: engine scripts not found');
  return files;
}

// The engine's source text, files joined in load order (for hashes and source checks).
function source(dir = root) {
  return engineFiles(dir).map(file => fs.readFileSync(path.join(dir, file), 'utf8')).join('\n');
}

// Runs the engine in a vm context, file by file as the browser does; returns the context.
function load(context, dir = root) {
  for (const file of engineFiles(dir)) vm.runInContext(fs.readFileSync(path.join(dir, file), 'utf8'), context, { filename: file });
  return context;
}

module.exports = { engineFiles, source, load };
