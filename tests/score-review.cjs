const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const report=JSON.parse(fs.readFileSync('data/score-v3-review.json'));
assert.equal(report.version,'3.0');
assert.equal(report.sourceCodeHashes.v3,hash('script.js'));
assert.equal(report.sourceCodeHashes.v21,hash('tools/legacy/scoring-v2.1.js'));
for(const [name,d] of Object.entries(report.datasets)){
 assert.equal(d.inputSha256,hash(`data/${name}.json`));
 assert.equal(d.v3.positive+d.v3.zero+d.v3.unevaluated,d.rows);
 for(const s of Object.values(d.sensitivity)){
  assert(s.spearmanPositiveOnly===null||s.spearmanPositiveOnly>=-1&&s.spearmanPositiveOnly<=1);
  assert(s.topKOverlap<=s.topK);
 }
 assert(d.reviewQueue.every(x=>x.reviewStatus==='queued-not-ground-truth'));
}
for(const f of ['coverage','decp-coverage','decp-cities-coverage','consultations-coverage','tours-notices-coverage','colombia-secop2-coverage'])assert.equal(JSON.parse(fs.readFileSync(`data/${f}.json`)).currentIndex.version,'3.0');
const checks=JSON.parse(fs.readFileSync('data/international-access-checks.json')).checks;
assert(checks.some(c=>c.url.includes('jbjy-vk9h.json')&&c.http_status===200));
assert(checks.some(c=>c.url.includes('swagger.json')&&c.global_security));
assert(checks.filter(c=>c.url.includes('pncp.gov.br/api')).every(c=>c.http_status!==200),'No successful PNCP response was recorded in these checks.');
assert(checks.some(c=>c.url.includes('/ocds/record/ocds-03ad3f')&&c.http_status===200&&c.license&&c.license.includes('creativecommons.org/licenses/by/4.0')),'Paraguay record must be 200 with CC BY 4.0.');
assert(checks.some(c=>c.url.includes('/search/processes')&&c.http_status===200),'Paraguay date-filtered search must be 200.');
assert(checks.some(c=>c.url.includes('/parameters/parameters')&&c.http_status===200),'Paraguay parameters catalogue must be 200.');
console.log('Review report source hashes, counts, sensitivity bounds, version pointers and international access claims verified.');
