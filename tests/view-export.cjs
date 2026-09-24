const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx=vm.createContext({URL,URLSearchParams});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
const run=(fn,...args)=>{ctx.args=args;return vm.runInContext(`${fn}(...args)`,ctx);};

// URL fragment state: defaults omitted, round trip exact, junk rejected.
const view=run('hashToViewState','');
assert.equal(run('viewStateToHash',{...view,dataset:''}),'');
const shared={...view,dataset:'colombia',search:'Caldas & "bomberos"',sort:'amount',minimum:'1000','min-score':'40',indicator:'secop2-long-duration',flagged:true,page:3,pageSize:100};
const hash=run('viewStateToHash',shared);
assert.match(hash,/^#dataset=colombia&q=/);
assert.ok(!/flagged=false|official|page=1\b|size=50/.test(hash));
const back=run('hashToViewState',hash);
for(const key of Object.keys(shared))assert.deepEqual(back[key],shared[key],key);
const junk=run('hashToViewState','#page=-4&size=7&flagged=yes');
assert.equal(junk.page,1);assert.equal(junk.pageSize,50);assert.equal(junk.flagged,false);assert.equal(junk.sort,'score');assert.equal(junk['min-score'],'0');

// Export: every filtered row, unknown stays empty (never zero), formulas neutralized, currency kept.
const cities=run('prepareContracts',JSON.parse(fs.readFileSync('data/decp-cities.json')));
const colombia=run('prepareContracts',JSON.parse(fs.readFileSync('data/colombia-secop2.json')));
const notAssessed=cities.find(c=>run('getVigilanceScore',c)==null);
const named=cities.find(c=>c.supplierProfiles?.length);
const co=colombia.find(c=>c.contractId==='CO1.PCCNTR.6685724');
const formula={...named,id:'test-formula',description:'=HYPERLINK("http://x","y")',supplier:'+33 1 23',buyer:'@SUM(A1)'};
const rows=[notAssessed,named,co,formula];
const csv=run('rowsToCsv',rows);
const lines=csv.trimEnd().split('\r\n');
assert.equal(lines[0],vm.runInContext('EXPORT_COLUMNS',ctx).join(','));
assert.equal(lines.length,rows.length+1);
const exported=rows.map(c=>run('exportRecord',c));
assert.equal(exported[0].index,null);assert.equal(exported[0].indexStatus,'not assessed');
assert.match(lines[1],/,not assessed,/);assert.ok(!/,0,not assessed,/.test(lines[1]));
assert.equal(exported[1].supplierCurrentName,named.supplierProfiles.map(p=>p.name).join('; '));
assert.equal(exported[2].currency,'COP');assert.equal(exported[2].buyerId,co.buyerNit);
assert.match(exported[2].source,/^https:\/\/community\.secop\.gov\.co\//);
assert.ok(lines[4].includes(`"'=HYPERLINK(""http://x"",""y"")"`));
assert.ok(lines[4].includes(",'+33 1 23,")&&lines[4].includes(",'@SUM(A1),"));
const json=JSON.parse(run('rowsToJson',rows,{dataset:'Test',view:hash,exportedAt:'2026-09-24T00:00:00Z'}));
assert.equal(json.count,4);assert.equal(json.records[0].index,null);assert.match(json.caveat,/not proof of wrongdoing/);
assert.equal(json.scoreVersion,vm.runInContext('SCORE_VERSION',ctx));assert.equal(json.view,hash);
console.log('URL view state round-trips without defaults; CSV/JSON exports keep unknowns empty, currencies, sources and neutralize formulas.');
