// Offline diagnostics only. No fitting to corruption labels, no country comparison.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
function engine(file){const code=fs.readFileSync(path.join(root,file),'utf8'),c=vm.createContext({URL});vm.runInContext(code,c);return {hash:hash(code),call(fn,...args){c.args=args;return vm.runInContext(`${fn}(...args)`,c);}};}
const old=engine('tools/legacy/scoring-v2.1.js'),current=engine('script.js');
const datasets=['contracts','decp-history','decp-cities','consultations','tours-notices'];
function ranks(values){const pairs=values.map((value,i)=>({value,i})).sort((a,b)=>b.value-a.value);const ranks=[];for(let i=0;i<pairs.length;){let end=i+1;while(end<pairs.length&&pairs[end].value===pairs[i].value)end++;const rank=(i+1+end)/2;for(let k=i;k<end;k++)ranks[pairs[k].i]=rank;i=end;}return ranks;}
function correlation(a,b){if(a.length<2)return null;const ar=ranks(a),br=ranks(b),mean=(a.length+1)/2;let xy=0,xx=0,yy=0;for(let i=0;i<a.length;i++){const x=ar[i]-mean,y=br[i]-mean;xy+=x*y;xx+=x*x;yy+=y*y;}return xx&&yy?Math.round(xy/Math.sqrt(xx*yy)*10000)/10000:null;}
function altScore(indicators,multipliers){const families={competition:0,execution:0};for(const i of indicators)families[i.family]=Math.max(families[i.family],i.weight*(multipliers[i.family]||1));return Math.round(Math.min(100,families.competition+families.execution)*10)/10;}
const report={version:'3.0',generatedAt:new Date().toISOString(),sourceCodeHashes:{v21:old.hash,v3:current.hash},
 interpretation:'Editorial triage, not probability. Threshold eligibility is not statistical calibration. Null is unevaluated, not a negative. Official findings are separate evidence. No target fraction of flagged contracts.',
 coverageDefinition:'evaluated/applicable-known checks plus separately displayed unknown-applicability checks; no normalization by missingness',
 changes:['Amounts do not amplify scores; direct awards and direct repetition include all amounts.','Amount evolution uses comparable relative increase >20%, no EUR50000 threshold.','Single-bid rule requires explicitly competitive procedure, not presumed from missing directAward.','All initial/modification conflicts, duplicate DECP identifiers, unverified dossiers excluded; aggregate audits not individual scoring units.','Official findings removed from heuristic points, still available as evidence/filter/sort.'],
 sensitivityMethod:'Diagnostic reweighting of competition/execution by 0.8/1.2 and 1.2/0.8. Same eligibility, maxima and cap. Spearman uses average ranks for ties, positive baseline scores only, null/zero excluded. Top-20 uses id tie-break solely for reproducibility; ties at cutoff reported. Not validation against ground truth.',
 reviewMethod:'Queues selected by SHA256(id), two per signal/zero/unevaluated stratum per dataset. This is a reproducible reading queue, NOT completed human review or labelled ground truth.',datasets:{}};
for(const file of datasets){
 const content=fs.readFileSync(path.join(root,`data/${file}.json`),'utf8'),data=JSON.parse(content);
 const v2=old.call('prepareContracts',data),v3=current.call('prepareContracts',data);
 const oldMap=new Map(v2.map(c=>[c.id,old.call('getVigilanceScore',c)]));
 const entries=v3.map(c=>{const b=current.call('getScoreBreakdown',c);return {c,score:b.score,assessment:b.assessment,indicators:current.call('getIndicators',c),oldScore:oldMap.get(c.id)};});
 const indicators={};for(const x of entries)for(const i of x.indicators)indicators[i.id]=(indicators[i.id]||0)+1;
 const positive=entries.filter(x=>x.score>0);
 const ranked=[...positive].sort((a,b)=>b.score-a.score||a.c.id.localeCompare(b.c.id));
 const k=Math.min(20,ranked.length),top=new Set(ranked.slice(0,k).map(x=>x.c.id)),cutoff=k?ranked[k-1].score:null;
 const scenarios={};
 for(const [name,multipliers] of Object.entries({competitionLower:{competition:.8,execution:1.2},executionLower:{competition:1.2,execution:.8}})){
  const scores=positive.map(x=>altScore(x.indicators,multipliers));
  const ordered=positive.map((x,i)=>({id:x.c.id,score:scores[i]})).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));
  const altCutoff=k?ordered[k-1].score:null;
  scenarios[name]={multipliers,spearmanPositiveOnly:correlation(positive.map(x=>x.score),scores),positiveRows:positive.length,topK:k,topKOverlap:ordered.slice(0,k).filter(x=>top.has(x.id)).length,baselineCutoff:cutoff,baselineCutoffTies:ranked.filter(x=>x.score===cutoff).length,scenarioCutoffTies:ordered.filter(x=>x.score===altCutoff).length};
 }
 const summary={rows:entries.length,inputSha256:hash(content),officialFindings:entries.filter(x=>x.c.officialFinding===true).length,
  v21:{positive:entries.filter(x=>x.oldScore>0).length,zero:entries.filter(x=>x.oldScore===0).length},
  v3:{positive:positive.length,zero:entries.filter(x=>x.score===0).length,unevaluated:entries.filter(x=>x.score===null).length,excluded:entries.filter(x=>x.assessment.excludedReason).length,indicators,
   meanEvaluatedChecks:Math.round(entries.reduce((n,x)=>n+x.assessment.evaluated,0)/entries.length*100)/100},
  transitions:{positiveToZero:entries.filter(x=>x.oldScore>0&&x.score===0).length,positiveToUnevaluated:entries.filter(x=>x.oldScore>0&&x.score===null).length,zeroToPositive:entries.filter(x=>x.oldScore===0&&x.score>0).length},
  sensitivity:scenarios,reviewQueue:[]};
 for(const [stratum,filter] of Object.entries({signal:x=>x.score>0,zero:x=>x.score===0,unevaluated:x=>x.score===null})){
  const chosen=entries.filter(filter).sort((a,b)=>hash(a.c.id).localeCompare(hash(b.c.id))).slice(0,2);
  summary.reviewQueue.push(...chosen.map(x=>({stratum,id:x.c.id,source:x.c.source,oldScore:x.oldScore,v3Score:x.score,signals:x.indicators.map(i=>i.id),evaluated:x.assessment.evaluated,applicableKnown:x.assessment.applicable,unknownApplicability:x.assessment.unknownApplicability,excludedReason:x.assessment.excludedReason,reviewStatus:'queued-not-ground-truth'})));
 }
 report.datasets[file]=summary;
}
fs.writeFileSync(path.join(root,'data/score-v3-review.json'),JSON.stringify(report,null,2)+'\n');
// Preserve historic coverage snapshots/rule counts; explicitly point at current index.
for(const name of ['coverage','decp-coverage','decp-cities-coverage','consultations-coverage','tours-notices-coverage']){
 const dest=path.join(root,`data/${name}.json`);const coverage=JSON.parse(fs.readFileSync(dest));
 coverage.currentIndex={version:'3.0',report:'score-v3-review.json',note:'Earlier rule/count sections describe their preparation version, not the active v3 index. Source cohorts unchanged; unknown scores are null, findings separate.'};
 fs.writeFileSync(dest,JSON.stringify(coverage,null,2)+'\n');
}
console.log(Object.fromEntries(Object.entries(report.datasets).map(([name,d])=>[name,d.v3])));
