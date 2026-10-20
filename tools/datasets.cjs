// The explorer's dataset list (datasets.js) for Node tools and tests; Python: common.datasets().
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const PREFIX = 'globalThis.DATASETS = ';

function readDatasets(dir = root) {
  const text = fs.readFileSync(path.join(dir, 'datasets.js'), 'utf8');
  const start = text.indexOf(PREFIX);
  if (start < 0) throw new Error('datasets.js: DATASETS not found');
  return JSON.parse(text.slice(start + PREFIX.length).trim().replace(/;$/, ''));
}

// Every published file (not coverage or raw files), once, in menu order. A dataset may load several files
// (the merged France DECP dataset); remote datasets have none here.
function datasetPaths(datasets = readDatasets()) {
  const paths = Object.values(datasets).flatMap(d => d.path ? [].concat(d.path) : []);
  if (!paths.length || new Set(paths).size !== paths.length || paths.some(p => !/^data\/[^.]+.*\.json$/.test(p))) throw new Error('Invalid dataset paths');
  return paths;
}

// Files the browser loads for each local dataset: the slim copies where they exist (tools/build-web-data.py).
function browserFiles(datasets = readDatasets()) {
  return Object.fromEntries(Object.entries(datasets).filter(([, d]) => d.path).map(([key, d]) => [key, d.web || [].concat(d.path)]));
}

module.exports = { readDatasets, datasetPaths, browserFiles };
