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
// Brazil PNCP: the September 400 was an invalid page size (valid 10..500), the timeouts transient.
// Access is established without a token (2026-09-25); no licence is declared in the API document.
const pncp=checks.filter(c=>c.url.includes('pncp.gov.br/api')&&c.label.includes('diagnosis'));
assert(pncp.some(c=>/tamanhoPagina=1(&|$)/.test(c.url)&&c.http_status===400&&/Tamanho de página inválido/.test(c.error_body||'')),'PNCP page size 1 must be recorded as an invalid-size 400.');
assert(pncp.some(c=>/tamanhoPagina=501/.test(c.url)&&c.http_status===400),'PNCP page size 501 must be recorded as 400.');
assert(pncp.some(c=>/tamanhoPagina=500/.test(c.url)&&c.http_status===200),'PNCP page size 500 must be recorded as 200.');
assert(pncp.some(c=>c.url.includes('cnpjOrgao=')&&c.http_status===200),'PNCP buyer filter must be recorded as 200.');
assert(checks.some(c=>c.url.includes('/ocds/record/ocds-03ad3f')&&c.http_status===200&&c.license&&c.license.includes('creativecommons.org/licenses/by/4.0')),'Paraguay record must be 200 with CC BY 4.0.');
assert(checks.some(c=>c.url.includes('/search/processes')&&c.http_status===200),'Paraguay date-filtered search must be 200.');
assert(checks.some(c=>c.url.includes('/parameters/parameters')&&c.http_status===200),'Paraguay parameters catalogue must be 200.');
console.log('Review report source hashes, counts, sensitivity bounds, version pointers and international access claims verified.');
