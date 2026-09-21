// Optional offline preparation/verification, not required to serve the static site.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({ URL });
vm.runInContext(fs.readFileSync(path.join(root, 'script.js'), 'utf8'), context);
context.data = JSON.parse(fs.readFileSync(path.join(root, 'data/decp-cities.json'), 'utf8'));
const metrics = vm.runInContext(`(() => {
 const rows = prepareContracts(data);
 const indicators = {};
 for (const r of rows) for (const i of getIndicators(r)) indicators[i.id] = (indicators[i.id] || 0) + 1;
 const competition = new Map(rows.filter(r => r.competitionContext).map(r => [r.buyerSiret+':'+r.competitionContext.cpvGroup,r.competitionContext]));
 const suppliers = new Map(rows.filter(r => r.supplierContext).map(r => [r.buyerSiret+':'+r.supplierContext.cpvGroup,r.supplierContext]));
 return {version:SCORE_VERSION, scoreFormula:'min(100, max(competition) + max(execution)); null if no check evaluated; official findings separate',
   exclusion:'All initial or modification conflicts in this city cohort: no indicators, excluded from longitudinal denominators. Excluded rows are unevaluated (null), not zero. Zero requires at least one evaluated check.',
   triggeredContracts:indicators,
   contractsWithAnyIndicator:rows.filter(r => getIndicators(r).length).length,
   unevaluated:rows.filter(r => getVigilanceScore(r) == null).length,
   zero:rows.filter(r => getVigilanceScore(r) === 0).length,
   officialFindings:rows.filter(r => r.officialFinding === true).length,
   amountEvolutionAvailable:rows.filter(r => getAmountEvolution(r).status==='available').length,
   repeatedSingleBid:{eligibleGroups:competition.size,sufficientGroups:[...competition.values()].filter(c=>c.sufficient).length,minimumKnown:10,minimumCoverage:0.8,minimumSingleShare:0.6},
   supplierConcentration:{eligibleGroupsWithIdentifiedHolder:suppliers.size,sufficientGroups:[...suppliers.values()].filter(c=>c.sufficient).length,minimumKnown:10,minimumCoverage:0.8,minimumShare:0.6},
   noTriggerRules:['amount-increase','supplier-concentration','repeated-direct-award','short-bidding-period'].filter(id => !indicators[id])};
})()`, context);
const destination = path.join(root, 'data/decp-cities-coverage.json');
const coverage = JSON.parse(fs.readFileSync(destination, 'utf8'));
coverage.indexV3Metrics = metrics;
coverage.currentIndex = {version:'3.0',report:'score-v3-review.json',note:'Earlier rule sections are historical preparation snapshots; indexV3Metrics describes the current code.'};
coverage.verification = {commands:['node tests/rules.cjs','node tests/scoring-v3.cjs','node tests/cities.cjs','python -m unittest discover -s tests -p "test_*.py"','node tests/browser.cjs'], note:'Tests are executable checks, not independent auditing of source accuracy.'};
fs.writeFileSync(destination, JSON.stringify(coverage, null, 2)+'\n');
console.log(JSON.stringify(metrics, null, 2));
