// Research only: odds ratio of each non-circular check against single bidding, per bundled cohort.
// Usage: node tools/single-bid-proxy.cjs .   Changes no score or dataset.
const fs=require('fs'),path=require('path'),vm=require('vm');
const root=process.argv[2];const c=vm.createContext({URL});vm.runInContext(fs.readFileSync(path.join(root,'script.js'),'utf8'),c);
const call=(fn,...a)=>{c.args=a;return vm.runInContext(`${fn}(...args)`,c);};
const outcome=/^(single-bid|[a-z]+-single-offer|dncp-single-tenderer)$/, circular=/repeated-single|repeated-plurality|single-tenderer|single-offer|single-bid|better-bid/;
for(const f of ['contracts','decp-history','decp-cities','ted-czechia','ted-portugal','ted-romania','paraguay-dncp-3buyers','prozorro','uk-fts','chile-mp']){
 const rows=call('prepareContracts',JSON.parse(fs.readFileSync(path.join(root,'data',f+'.json'))));
 const t={};
 for(const r of rows){const ch=call('getAssessment',r).checks;const o=ch.find(k=>outcome.test(k.id));if(!o||!['signal','clear'].includes(o.status))continue;const y=o.status==='signal';
  for(const k of ch){if(circular.test(k.id)||!['signal','clear'].includes(k.status))continue;const x=k.status==='signal';(t[k.id]??=[0,0,0,0])[(x?0:2)+(y?0:1)]++;}}
 console.log('\n##',f);
 for(const[k,[a,b,cc,d]]of Object.entries(t)){if(a+b===0){console.log(' ',k,'never fires among single-bid-known rows (n='+(cc+d)+')');continue;}
  const or=((a+.5)*(d+.5))/((b+.5)*(cc+.5)),se=Math.sqrt(1/(a+.5)+1/(b+.5)+1/(cc+.5)+1/(d+.5));
  console.log(' ',k,`flag&single=${a} flag&multi=${b} noflag&single=${cc} noflag&multi=${d}  OR=${or.toFixed(2)} [${Math.exp(Math.log(or)-1.96*se).toFixed(2)}, ${Math.exp(Math.log(or)+1.96*se).toFixed(2)}]`);}
}
