'use strict';

const HISTORY_COHORT = 'decp-paris-ardeche-2024-2025';
const CITIES_COHORT = 'decp-six-cities-2024-2025';
const HISTORY_COHORTS = new Set([HISTORY_COHORT, CITIES_COHORT]);
function isAmbiguousCityContract(c) {
  return c.cohortId === CITIES_COHORT && Boolean(c.initialConflicts?.length || c.modificationConflicts?.length);
}
const HISTORY_START = '2024-01-01';
const HISTORY_END = '2025-12-31';

const SCORE_VERSION = '2.1';

// Conservative calendar-day upper bound: publication time is not supplied by BOAMP.
function getBiddingPeriod(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  const c = contract.consultation;
  if (!c) return unavailable('Avis initial et calendrier non importés.');
  if (!c.searchComplete) return unavailable('Complétude des versions non démontrée ; aucun point de délai.');
  if (!c.procedureId || !c.lotId) return unavailable('Identifiant de procédure ou de lot manquant.');
  if (c.exclusions?.length) return unavailable('Chronologie exclue : ' + c.exclusions.join(' '));
  const notices = c.notices;
  if (!Array.isArray(notices) || notices.filter(n => n.kind === 'initial').length !== 1) return unavailable('Avis initial ambigu.');
  const initial = notices.find(n => n.kind === 'initial');
  if (initial.id !== c.initialNoticeId) return unavailable('Référence initiale incompatible.');
  const ordered = [...notices].sort((a, b) => (a.publicationDate || '').localeCompare(b.publicationDate || ''));
  const seen = new Set();
  for (const n of ordered) {
    if (!['initial', 'correction'].includes(n.kind) || seen.has(n.id) || !safeSource(n.source) || !n.version ||
        !/^\d{4}-\d{2}-\d{2}$/.test(n.publicationDate || '') || !Number.isFinite(Date.parse(n.publicationDate)) ||
        new Date(n.publicationDate).toISOString().slice(0, 10) !== n.publicationDate) return unavailable('Version, source ou publication ambiguë.');
    if (n.kind === 'correction' && (!(n.previousNoticeIds || []).some(id => seen.has(id)) || n.publicationDate <= initial.publicationDate)) return unavailable('Correction non reliée ou ordre ambigu.');
    if (n.procedureType !== 'open' || n.accelerated !== false) return unavailable('Procédure autre qu’ouverte non accélérée, ou accélération inconnue.');
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/.test(n.deadline || '') || !Number.isFinite(Date.parse(n.deadline))) return unavailable('Date limite ou fuseau inconnu ; ne pas reporter silencieusement l’ancienne échéance.');
    const deadlineDay = n.deadline.slice(0, 10);
    if (new Date(deadlineDay).toISOString().slice(0, 10) !== deadlineDay) return unavailable('Date limite invalide.');
    if (Date.parse(n.deadline) <= Date.parse(n.publicationDate)) return unavailable('Échéance antérieure à la publication.');
    seen.add(n.id);
  }
  if (ordered[0] !== initial || new Set(ordered.map(n => n.publicationDate)).size !== ordered.length) return unavailable('Ordre des versions ambigu.');
  // A shortened deadline or correction after the previous deadline needs manual review.
  for (let i = 1; i < ordered.length; i++) {
    if (Date.parse(ordered[i].deadline) < Date.parse(ordered[i - 1].deadline) || Date.parse(ordered[i].publicationDate) > Date.parse(ordered[i - 1].deadline)) return unavailable('Réduction ou réouverture de délai : revue manuelle requise.');
  }
  const latest = ordered[ordered.length - 1];
  const days = (Date.parse(latest.deadline) - Date.parse(initial.publicationDate + 'T00:00:00Z')) / 86400000;
  return { status: 'available', days, initialPublication: initial.publicationDate, deadline: latest.deadline, short: days < 15 };
}
const CPV_SECTORS = {
  '03': 'Agriculture et pêche', '09': 'Énergie et combustibles', '14': 'Mines et minéraux',
  '15': 'Alimentation et boissons', '16': 'Machines agricoles', '18': 'Vêtements et équipements',
  '19': 'Cuir et textiles', '22': 'Imprimés et édition', '24': 'Produits chimiques',
  '30': 'Matériel informatique et de bureau', '31': 'Matériel électrique', '32': 'Télécommunications — matériel',
  '33': 'Matériel médical et pharmacie', '34': 'Véhicules et transport — matériel', '35': 'Sécurité et défense — matériel',
  '37': 'Musique, sport et loisirs — matériel', '38': 'Mesure, laboratoire et optique', '39': 'Mobilier et équipements divers',
  '41': 'Eau collectée et épurée', '42': 'Machines industrielles', '43': 'Machines de construction et extraction',
  '44': 'Matériaux de construction', '45': 'Travaux de construction', '48': 'Logiciels',
  '50': 'Réparation et entretien', '51': 'Installation', '55': 'Hôtellerie et restauration',
  '60': 'Transport', '63': 'Transport — services auxiliaires', '64': 'Poste et télécommunications',
  '65': 'Services de distribution', '66': 'Finance et assurance', '70': 'Immobilier',
  '71': 'Architecture, ingénierie et contrôle', '72': 'Services informatiques', '73': 'Recherche et développement',
  '75': 'Administration, défense et sécurité sociale', '76': 'Services pétroliers et gaziers',
  '77': 'Services agricoles et forestiers', '79': 'Conseil, communication et services aux entreprises',
  '80': 'Éducation et formation', '85': 'Santé et action sociale', '90': 'Déchets, assainissement et environnement',
  '92': 'Culture, loisirs et sport', '98': 'Autres services'
};

function getSector(contract) {
  const code = /^\d{8}(?:-\d)?$/.test(contract.cpv || '') ? contract.cpv.slice(0, 2) : null;
  return code && CPV_SECTORS[code] ? { code, label: CPV_SECTORS[code] } : { code: 'unknown', label: 'Secteur non renseigné' };
}

function getSupplierIdentity(contract) {
  const ids = [...new Set((contract.supplierIds || []).map(s => {
    if (s.identifierType === 'SIRET' && /^\d{14}$/.test(s.id)) return s.id.slice(0, 9);
    if (s.identifierType === 'SIREN' && /^\d{9}$/.test(s.id)) return s.id;
    return null;
  }).filter(Boolean))];
  return (contract.supplierIds || []).length === 1 && ids.length === 1 ? ids[0] : null;
}

function amountTier(amount) {
  if (!Number.isFinite(amount) || amount < 0) return 0;
  return [100000, 500000, 1000000, 5000000, 10000000].filter(threshold => amount >= threshold).length;
}
function indicatorSeverity(weight) {
  if (weight >= 40) return { id: 'extreme', label: 'Très élevé' };
  if (weight >= 25) return { id: 'high', label: 'Élevé' };
  if (weight >= 12) return { id: 'moderate', label: 'Modéré' };
  return { id: 'low', label: 'Faible' };
}
function hasIncompleteData(contract) {
  return contract.dataStatus !== 'verified' || Boolean(contract.initialConflicts?.length || contract.modificationConflicts?.length) ||
    [contract.amount, contract.offers, contract.durationMonths, contract.directAward].some(value => value == null);
}
function scoreLevel(score, incomplete = false) {
  if (score === 0) return incomplete ? { id: 'unknown', label: 'Données partielles' } : { id: 'none', label: 'Aucun signal déclenché' };
  if (score < 20) return { id: 'low', label: 'Vigilance faible' };
  if (score < 40) return { id: 'moderate', label: 'Vigilance modérée' };
  if (score < 70) return { id: 'high', label: 'Vigilance élevée' };
  return { id: 'extreme', label: 'Vigilance très élevée' };
}

// Explicit published citations only; never used by scoring or identity matching.
function getLegalContext(contract) {
  if (contract.dataFamily === 'audit' || !safeSource(contract.source)) return [];
  const citations = [];
  for (const field of ['description', 'procedure']) {
    const text = contract[field];
    if (typeof text !== 'string') continue;
    const pattern = /\bR[.\s–—-]*2122\s*[-–—]\s*(\d+)(?:\s*[-–—]?\s*\d+\s*°)?/gi;
    for (const match of text.matchAll(pattern)) {
      const article = `R2122-${match[1]}`;
      if (citations.some(c => c.article === article && c.field === field)) continue;
      citations.push({ article, citation: match[0], field, excerpt: text, source: contract.source,
        label: article === 'R2122-1' ? 'Urgence impérieuse — article cité' : article === 'R2122-3' ? 'Raisons artistiques, techniques ou droits exclusifs — article cité' : 'Autre fondement R2122 cité' });
    }
  }
  return citations;
}

function getIndicators(contract) {
  // Reused/conflicting city contract identifiers are not reliable scoring units.
  if (isAmbiguousCityContract(contract)) return [];
  const indicators = [];
  const tier = amountTier(contract.amount);
  function add(id, label, weight, family, explanation) {
    const severity = indicatorSeverity(weight);
    indicators.push({ id, label, weight, family, severity: severity.id, severityLabel: severity.label, explanation });
  }
  if (contract.offers === 1) add('single-bid', '1 seule offre', contract.directAward === true ? 5 : 8 + tier * 3, 'competition',
    contract.directAward === true ? 'Une offre est déclarée. C’est attendu dans une attribution sans concurrence : ce signal a un poids réduit de 5 et ne s’ajoute pas au signal d’attribution directe.' : 'Une seule offre reçue est déclarée, sans présumer sa recevabilité. Poids : 8 + 3 par tranche de montant. Une spécialisation du marché peut expliquer le faible nombre d’offres.');
  if (contract.directAward === true && contract.amount >= 100000) add('direct-award', 'Attribution sans concurrence > 100 k€', 25 + tier * 5, 'competition',
    'Attribution sans concurrence d’au moins 100 000 €. Poids : 25 + 5 par tranche de montant, soit 30 à 50. La justification et les exceptions légales doivent être examinées : une attribution directe n’est pas automatiquement irrégulière.');
  if (contract.durationMonths >= 120) add('long-contract', 'Durée ≥ 10 ans', Math.min(25, 8 + Math.floor((contract.durationMonths - 120) / 60) * 5 + tier), 'execution',
    'Durée déclarée d’au moins 120 mois. Poids : 8 + 5 par période entière de cinq ans au-delà de dix ans + tranche de montant, plafonné à 25. La durée peut être justifiée, notamment par des investissements ; durée initiale et reconductions doivent être distinguées.');
  if (contract.officialFinding === true) add('official-finding', 'Constat officiel', 50, 'official',
    'Observation documentée d’une CRC ou décision d’une autorité sur le contrat ou l’ensemble de commandes décrit. Poids éditorial fixe de 50, indépendant du montant et de la gravité juridique. Ce n’est pas nécessairement une condamnation. Lire le passage, le périmètre et les réponses.');
  const bidding = getBiddingPeriod(contract);
  if (bidding.status === 'available' && bidding.short) add('short-bidding-period', 'Délai de réponse court', 12, 'competition',
    `Moins de 15 jours calendaires depuis la publication initiale jusqu’à la dernière échéance (${bidding.days.toFixed(2)} jours, borne haute depuis minuit UTC). Procédure ouverte explicitement non accélérée, versions reliées et calendrier vérifié. Poids éditorial fixe 12, non additionné aux autres signaux de concurrence. Ce n’est pas un seuil légal ni une comparaison statistique ; justifications à examiner.`);
  const evolution = getAmountEvolution(contract);
  if (evolution.status === 'available' && evolution.percentage > 20 && evolution.delta > 50000) add('amount-increase', 'Montant déclaré en hausse',
    Math.min(40, 15 + amountTier(evolution.delta) * 5 + (evolution.percentage >= 50 ? 5 : 0) + (evolution.percentage >= 100 ? 5 : 0)), 'execution',
    'Nouveau montant déclaré supérieur à l’initial de plus de 20 % et de plus de 50 000 €, sur un prix déclaré définitif ferme. Poids : 15 + 5 par tranche de hausse en euros + 5 à partir de 50 % + 5 à partir de 100 %, plafonné à 40. Des quantités ou prestations supplémentaires peuvent expliquer cette hausse ; ce n’est pas une mesure de surcoût injustifié ou de paiement.');
  const context = contract.competitionContext;
  if (contract.offers === 1 && context?.sufficient && context.rate >= 0.6) add('repeated-single-bid', 'Faible concurrence répétée',
    Math.min(40, (context.rate >= 0.8 ? 30 : 20) + tier * 2), 'competition',
    `${context.single}/${context.known} contrats concurrentiels au nombre d’offres connu du même acheteur et CPV ${context.cpvGroup} ont reçu une seule offre en 2024–2025. Minimum : 10 observations, 80 % de couverture et 60 % à une offre. Poids : 20 (30 si taux ≥ 80 %) + 2 par tranche de montant, plafond 40. Le contrat doit lui-même avoir reçu une seule offre.`);
  const supplier = contract.supplierContext;
  if (supplier?.sufficient && supplier.share >= 0.6) add('supplier-concentration', 'Attributions concentrées',
    Math.min(30, (supplier.share >= 0.95 ? 25 : supplier.share >= 0.8 ? 20 : 12) + tier), 'competition',
    `Le même SIREN reçoit ${supplier.wins}/${supplier.known} contrats au titulaire unique renseigné, chez cet acheteur et CPV ${supplier.cpvGroup}, en 2024–2025. Minimum : 10 contrats au titulaire identifiable, 80 % de couverture, part ≥ 60 %. Poids : 12, 20 à partir de 80 %, 25 à partir de 95 %, + tranche de montant, plafond 30. Groupements et identifiants ambigus exclus ; cela peut refléter une spécialisation ou des accords-cadres, pas un favoritisme établi.`);
  if (contract.directAward === true && contract.amount >= 100000 && supplier?.directCount >= 3) add('repeated-direct-award', 'Attributions directes répétées',
    Math.min(55, 25 + tier * 5 + Math.min(10, (supplier.directCount - 3) * 2)), 'competition',
    `${supplier.directCount} contrats sans concurrence d’au moins 100 000 € sont publiés pour ce SIREN, cet acheteur et CPV ${supplier.cpvGroup} en 2024–2025. Chaque identifiant est compté une fois, sans groupe en conflit. Poids : 25 + 5 par tranche du montant de ce contrat + 2 par contrat au-delà de trois (bonus plafonné à 10), maximum 55. Les exceptions légales peuvent expliquer la répétition ; ce n’est pas une preuve d’irrégularité.`);
  return indicators;
}

function getScoreBreakdown(contract) {
  const families = { competition: 0, execution: 0, official: 0 };
  for (const indicator of getIndicators(contract)) families[indicator.family] = Math.max(families[indicator.family] || 0, indicator.weight);
  return { ...families, score: Math.min(100, Object.values(families).reduce((sum, value) => sum + value, 0)) };
}
function getVigilanceScore(contract) { return getScoreBreakdown(contract).score; }

function getAmountEvolution(contract) {
  const unavailable = reason => ({ status: 'unavailable', reason });
  if (contract.dataFamily !== 'decp' || !Array.isArray(contract.history)) return unavailable('Historique DECP non disponible.');
  if (!Array.isArray(contract.initialConflicts) || contract.initialConflicts.length) return unavailable('Valeurs initiales divergentes : aucun calcul de hausse.');
  if (Array.isArray(contract.modificationConflicts) && contract.modificationConflicts.length) return unavailable('Valeurs de modification divergentes pour un même identifiant : aucun calcul de hausse.');
  const initial = contract.history.find(event => event.kind === 'initial');
  const changes = contract.history.filter(event => event.kind === 'modification');
  if (!changes.length) return unavailable('Aucune modification publiée dans cet extrait ; cela ne prouve pas l’absence d’avenant.');
  if (!initial?.date || !(initial.amount > 0)) return unavailable('Montant ou date initiale non exploitable.');
  if (initial.amount !== contract.amount || initial.date !== contract.date) return unavailable('L’état initial de l’historique ne correspond pas aux champs du contrat.');
  if (changes.some(event => !event.date || event.date < initial.date)) return unavailable('Chronologie des modifications incomplète ou incohérente.');
  const ordered = [...changes].sort((a, b) => b.date.localeCompare(a.date));
  const latest = ordered[0];
  if (ordered.some(event => event.date === latest.date && event.amount !== latest.amount)) return unavailable('Plusieurs montants différents à la même date.');
  if (latest.amount == null) return unavailable('La dernière modification publiée ne renseigne pas de montant.');
  if (contract.priceType !== 'Définitif ferme') return unavailable('Prix non déclaré exclusivement définitif ferme : révision ou actualisation non isolable, aucun signal automatique.');
  if (changes.some(event => event.supplierId && !contract.supplierIds?.some(supplier => supplier.id === event.supplierId))) return unavailable('Changement de titulaire : périmètre à examiner manuellement.');
  if (latest.amount < initial.amount) return unavailable('Montant modifié inférieur à l’initial : baisse possible ou incrément mal saisi. Aucun incrément n’est additionné.');
  // Compare euro cents to avoid binary-float artefacts at the exact €50,000 threshold.
  const initialCents = Math.round(initial.amount * 100);
  const revisedCents = Math.round(latest.amount * 100);
  if (!Number.isSafeInteger(initialCents) || !Number.isSafeInteger(revisedCents) || initialCents <= 0) return unavailable('Montants hors précision monétaire exploitable.');
  const deltaCents = revisedCents - initialCents;
  return { status: 'available', initialAmount: initialCents / 100, revisedAmount: revisedCents / 100, delta: deltaCents / 100, percentage: deltaCents / initialCents * 100, date: latest.date };
}

// Retrospective context on the COMPLETE loaded cohort, never on filtered/page rows.
function prepareContracts(data) {
  const contracts = validateContracts(data).map(c => ({ ...c, competitionContext: null, supplierContext: null }));
  const groups = new Map();
  const supplierGroups = new Map();
  const identityCounts = new Map();
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !c.buyerSiret || !c.contractId) continue;
    const identity = `${c.buyerSiret}:${c.contractId}`;
    identityCounts.set(identity, (identityCounts.get(identity) || 0) + 1);
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || isAmbiguousCityContract(c) ||
        !c.buyerSiret || !c.contractId || identityCounts.get(`${c.buyerSiret}:${c.contractId}`) !== 1 ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') || !c.date ||
        c.date < HISTORY_START || c.date > HISTORY_END || c.directAward !== false ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  for (const group of groups.values()) {
    const known = group.filter(c => Number.isInteger(c.offers) && c.offers > 0);
    const single = known.filter(c => c.offers === 1).length;
    const coverage = known.length / group.length;
    const rate = known.length ? single / known.length : null;
    const context = { total: group.length, known: known.length, single, coverage, rate,
      cpvGroup: group[0].cpv.slice(0, 3), start: HISTORY_START, end: HISTORY_END,
      sufficient: known.length >= 10 && coverage >= 0.8 };
    group.forEach(c => { c.competitionContext = context; });
  }
  for (const c of contracts) {
    if (c.dataFamily !== 'decp' || !HISTORY_COHORTS.has(c.cohortId) || isAmbiguousCityContract(c) || !c.buyerSiret || !c.contractId ||
        identityCounts.get(`${c.buyerSiret}:${c.contractId}`) !== 1 || !c.date || c.date < HISTORY_START || c.date > HISTORY_END ||
        !/^\d{8}-\d$/.test(c.cpv || '') || c.cpv.startsWith('000') ||
        !Array.isArray(c.initialConflicts) || c.initialConflicts.length) continue;
    const key = `${c.cohortId}:${c.buyerSiret}:${c.cpv.slice(0, 3)}`;
    if (!supplierGroups.has(key)) supplierGroups.set(key, []);
    supplierGroups.get(key).push(c);
  }
  for (const group of supplierGroups.values()) {
    const known = group.filter(c => getSupplierIdentity(c) !== null);
    const bySupplier = new Map();
    known.forEach(c => { const id = getSupplierIdentity(c); if (!bySupplier.has(id)) bySupplier.set(id, []); bySupplier.get(id).push(c); });
    group.forEach(c => {
      const id = getSupplierIdentity(c);
      if (id === null) return;
      const supplierRows = bySupplier.get(id);
      const context = { cpvGroup: c.cpv.slice(0, 3), total: group.length, known: known.length,
        wins: supplierRows.length, share: supplierRows.length / known.length, coverage: known.length / group.length,
        sufficient: known.length >= 10 && known.length / group.length >= 0.8,
        directCount: supplierRows.filter(row => row.directAward === true && row.amount >= 100000).length };
      c.supplierContext = context;
    });
  }
  return contracts;
}

function groupInfo(contract, mode) {
  if (mode === 'sector') { const sector = getSector(contract); return { key: `sector:${sector.code}`, label: `${sector.code === 'unknown' ? '' : sector.code + ' · '}${sector.label}` }; }
  if (mode === 'buyer') return { key: `buyer:${contract.buyerSiret || normalize(contract.buyer)}`, label: contract.buyer + (contract.buyerSiret ? ` · ${contract.buyerSiret}` : ' · rapprochement par nom, à vérifier') };
  if (mode === 'supplier') {
    const identity = getSupplierIdentity(contract);
    return identity ? { key: `supplier:${identity}`, label: `SIREN ${identity} · ${contract.supplier || 'Titulaire'}` } : { key: `supplier-unknown:${contract.id}`, label: `${contract.supplier || 'Titulaire inconnu'} · groupement ou identité non rapprochée` };
  }
  if (mode === 'project') return contract.project ? { key: `project:${contract.project.id}`, label: contract.project.title } : { key: 'project:unknown', label: 'Sans projet documenté — ces contrats ne constituent pas un même projet' };
  return { key: '', label: '' };
}

function arrangeGroups(contracts, mode) {
  if (!mode) return { rows: contracts, groups: new Map() };
  const groups = new Map();
  for (const c of contracts) {
    const info = groupInfo(c, mode);
    if (!groups.has(info.key)) groups.set(info.key, { ...info, contracts: [] });
    groups.get(info.key).contracts.push(c);
  }
  const ordered = [...groups.values()];
  if (mode === 'project') ordered.sort((a, b) => Number(a.key === 'project:unknown') - Number(b.key === 'project:unknown'));
  return { rows: ordered.flatMap(group => group.contracts), groups };
}

function normalize(value) {
  return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('fr');
}

function safeSource(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function validateNoticeEvidence(c) {
  const e = c.noticeEvidence;
  if (!e || typeof e !== 'object' || e.noticeId !== c.noticeId || e.lotId !== c.lotId || e.procedureId !== c.contractFolderId ||
      e.source !== c.source || !safeSource(e.source) || !['initial', 'correction', 'award'].includes(e.kind)) throw new Error(`${c.id} : périmètre de preuve d’avis incompatible.`);
  for (const key of ['noticeUuid', 'version', 'lotReference', 'procedureId', 'procedureReference', 'procedureType', 'procedureDescription', 'legalBasis', 'dispatchDate', 'dispatchTime', 'publicationDate', 'sourcePath']) {
    if (e[key] != null && typeof e[key] !== 'string') throw new Error(`${c.id} : champ documentaire ${key} invalide.`);
  }
  for (const key of ['accelerated', 'relaunch', 'deadlineConflict', 'inPublicationWindow']) if (e[key] != null && typeof e[key] !== 'boolean') throw new Error(`${c.id} : état documentaire invalide.`);
  for (const key of ['justifications', 'awardCriteria', 'documents', 'references', 'buyers', 'ted', 'sameProcedureNotices', 'linkedNoticeLots']) if (!Array.isArray(e[key])) throw new Error(`${c.id} : liste documentaire ${key} invalide.`);
  if (!e.deadline || ['date', 'time', 'iso'].some(k => e.deadline[k] != null && typeof e.deadline[k] !== 'string')) throw new Error(`${c.id} : échéance documentaire invalide.`);
  const texts = (item, keys) => item && keys.every(k => item[k] == null || typeof item[k] === 'string');
  for (const j of e.justifications) if (!texts(j, ['code', 'category', 'text', 'path']) || j.scope !== 'procedure' || j.source !== e.source) throw new Error(`${c.id} : motif sans portée/source valide.`);
  for (const a of e.awardCriteria) {
    if (!texts(a, ['type', 'name', 'description', 'formula', 'path']) || a.lotId !== e.lotId || a.source !== e.source || !Array.isArray(a.parameters)) throw new Error(`${c.id} : critère rattaché au mauvais lot/source.`);
    for (const p of a.parameters) if (!texts(p, ['code', 'codeList', 'rawValue']) || (p.value != null && (!Number.isFinite(p.value) || p.value < 0))) throw new Error(`${c.id} : pondération invalide.`);
  }
  for (const d of e.documents) if (!d || !safeSource(d.url) || typeof d.downloaded !== 'boolean') throw new Error(`${c.id} : document invalide.`);
  for (const r of e.references) if (!texts(r, ['id', 'kind', 'path']) || !Array.isArray(r.matchedNoticeIds) || r.matchedNoticeIds.some(id => typeof id !== 'string') || (r.tedSource != null && !safeSource(r.tedSource))) throw new Error(`${c.id} : référence d’avis invalide.`);
  for (const b of e.buyers) if (!texts(b, ['id', 'name', 'siret'])) throw new Error(`${c.id} : acheteur documentaire invalide.`);
  for (const t of e.ted) if (!texts(t, ['version', 'publicationNumber', 'publicationDate', 'deadlineDate', 'deadlineTime', 'retrievedAt']) || t.noticeUuid !== e.noticeUuid || (t.lotId != null && t.lotId !== e.lotId) || typeof t.versionMatches !== 'boolean' || t.versionMatches !== (t.version === e.version) || !safeSource(t.source) || !/^data\/tours-notices\/raw\/ted-\d+-\d{4}\.xml$/.test(t.localFile || '')) throw new Error(`${c.id} : rapprochement TED invalide.`);
  for (const n of e.linkedNoticeLots) if (!texts(n, ['noticeId', 'lotId', 'version', 'kind', 'publicationDate', 'deadline', 'relation', 'basis']) || n.lotId !== e.lotId || !safeSource(n.source)) throw new Error(`${c.id} : lien de lot documentaire invalide.`);
  for (const n of e.sameProcedureNotices) if (!n || typeof n.id !== 'string' || !safeSource(n.source)) throw new Error(`${c.id} : lien de procédure invalide.`);
}

function validateContracts(data) {
  if (!Array.isArray(data)) throw new Error('Le fichier doit contenir un tableau JSON.');
  const ids = new Set();
  const projectDefinitions = new Map();
  for (const c of data) {
    if (!c || typeof c !== 'object' || typeof c.id !== 'string' || !c.id || ids.has(c.id)) {
      throw new Error('Chaque dossier doit posséder un identifiant texte unique.');
    }
    ids.add(c.id);
    for (const key of ['buyer', 'description']) {
      if (typeof c[key] !== 'string' || !c[key].trim()) throw new Error(`${c.id} : ${key} manquant.`);
    }
    for (const key of ['supplier', 'procedure', 'source', 'sourceLabel', 'sourceReference', 'notes', 'amountBasis', 'dateNote', 'reportUrl', 'responseLink', 'buyerSiret', 'contractId', 'lotId', 'noticeId', 'contractFolderId', 'cpv', 'publicationDate', 'priceType', 'priceForm', 'cohortId', 'identifierNote', 'nature', 'frameworkId', 'supplierNameSource']) {
      if (c[key] != null && typeof c[key] !== 'string') throw new Error(`${c.id} : ${key} doit être du texte.`);
    }
    for (const key of ['amount', 'offers', 'durationMonths']) {
      if (c[key] != null && (typeof c[key] !== 'number' || !Number.isFinite(c[key]) || c[key] < 0)) {
        throw new Error(`${c.id} : ${key} doit être un nombre positif ou nul, ou null.`);
      }
    }
    if (c.offers != null && !Number.isInteger(c.offers)) throw new Error(`${c.id} : nombre d’offres invalide.`);
    for (const key of ['directAward', 'officialFinding']) {
      if (c[key] != null && typeof c[key] !== 'boolean') throw new Error(`${c.id} : ${key} doit être booléen ou null.`);
    }
    if (c.date != null && (typeof c.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(c.date) || !Number.isFinite(Date.parse(c.date)) || new Date(c.date).toISOString().slice(0, 10) !== c.date)) {
      throw new Error(`${c.id} : date invalide (AAAA-MM-JJ ou null).`);
    }
    if (!['verified', 'unverified', 'synthetic'].includes(c.dataStatus)) throw new Error(`${c.id} : dataStatus requis (verified, unverified, synthetic).`);
    for (const key of ['source', 'reportUrl', 'responseLink', 'supplierNameSource']) {
      if (c[key] != null && !safeSource(c[key])) throw new Error(`${c.id} : lien ${key} HTTP(S) invalide.`);
    }
    if (c.project != null) {
      if (!c.project || typeof c.project !== 'object' || Array.isArray(c.project) ||
          typeof c.project.id !== 'string' || !/^[a-z0-9-]+$/.test(c.project.id) || typeof c.project.title !== 'string' || !c.project.title.trim() ||
          typeof c.project.basis !== 'string' || !c.project.basis.trim() || typeof c.project.source !== 'string' || !safeSource(c.project.source)) {
        throw new Error(`${c.id} : projet invalide.`);
      }
      if (c.project.evidence != null && (!Array.isArray(c.project.evidence) || c.project.evidence.some(e => !e ||
          typeof e !== 'object' || typeof e.label !== 'string' || !e.label.trim() || typeof e.description !== 'string' || !e.description.trim() || typeof e.type !== 'string' || !e.type.trim() ||
          typeof e.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(e.date) || !Number.isFinite(Date.parse(e.date)) ||
          new Date(e.date).toISOString().slice(0, 10) !== e.date || typeof e.source !== 'string' || !safeSource(e.source)))) throw new Error(`${c.id} : preuve de projet invalide.`);
      const definition = JSON.stringify([c.project.title, c.project.basis, c.project.source, c.project.evidence || []]);
      if (projectDefinitions.has(c.project.id) && projectDefinitions.get(c.project.id) !== definition) throw new Error(`${c.id} : métadonnées contradictoires pour le même projet.`);
      projectDefinitions.set(c.project.id, definition);
    }
    if (c.noticeEvidence != null) validateNoticeEvidence(c);
    if (c.consultation != null) {
      const timeline = c.consultation;
      if (!timeline || typeof timeline !== 'object' || typeof timeline.searchComplete !== 'boolean' ||
          !Array.isArray(timeline.notices) || !Array.isArray(timeline.exclusions) || timeline.exclusions.some(r => typeof r !== 'string')) throw new Error(`${c.id} : chronologie invalide.`);
      for (const key of ['procedureId', 'procedureReference', 'lotId', 'initialNoticeId']) if (timeline[key] != null && typeof timeline[key] !== 'string') throw new Error(`${c.id} : identifiant de consultation invalide.`);
      if (timeline.matchedAwards != null && !Array.isArray(timeline.matchedAwards)) throw new Error(`${c.id} : résultats liés invalides.`);
      if (timeline.lots != null && (!Array.isArray(timeline.lots) || timeline.lots.some(l => !l || typeof l !== 'object' || (l.cpv != null && !Array.isArray(l.cpv))))) throw new Error(`${c.id} : lots invalides.`);
      for (const n of [...timeline.notices, ...(timeline.matchedAwards || [])]) {
        for (const key of ['version', 'publicationState', 'publicationDate', 'deadline', 'procedureType', 'correctionText']) if (n?.[key] != null && typeof n[key] !== 'string') throw new Error(`${c.id} : champ d’avis ${key} invalide.`);
        if (!n || typeof n.id !== 'string' || !['initial', 'correction', 'award'].includes(n.kind) || !safeSource(n.source) ||
            (n.accelerated != null && typeof n.accelerated !== 'boolean') ||
            (n.previousNoticeIds != null && (!Array.isArray(n.previousNoticeIds) || n.previousNoticeIds.some(id => typeof id !== 'string')))) throw new Error(`${c.id} : avis de chronologie invalide.`);
      }
    }
    if (c.findingScope != null && !['contract', 'aggregate'].includes(c.findingScope)) throw new Error(`${c.id} : périmètre du constat invalide.`);
    if (c.amountQualifier != null && !['at-least', 'more-than', 'approximate'].includes(c.amountQualifier)) throw new Error(`${c.id} : précision du montant invalide.`);
    if (c.dataFamily != null && !['decp', 'boamp', 'audit'].includes(c.dataFamily)) throw new Error(`${c.id} : famille de données invalide.`);
    if (c.buyerSiret != null && !/^\d{14}$/.test(c.buyerSiret)) throw new Error(`${c.id} : SIRET acheteur invalide.`);
    if (c.supplierIds != null && (!Array.isArray(c.supplierIds) || c.supplierIds.some(s => !s || typeof s.id !== 'string' || (s.identifierType != null && typeof s.identifierType !== 'string')))) throw new Error(`${c.id} : identifiants fournisseurs invalides.`);
    if (c.supplierProfiles != null) {
      if (!Array.isArray(c.supplierProfiles)) throw new Error(`${c.id} : profils fournisseur invalides.`);
      const identities = new Set((c.supplierIds || []).map(s => s.identifierType === 'SIRET' && /^\d{14}$/.test(s.id) ? s.id.slice(0, 9) : s.identifierType === 'SIREN' && /^\d{9}$/.test(s.id) ? s.id : null).filter(Boolean));
      const seenProfiles = new Set();
      for (const p of c.supplierProfiles) {
        if (!p || !identities.has(p.siren) || seenProfiles.has(p.siren) || p.diffusionStatus !== 'O' || p.status !== 'available' ||
            typeof p.name !== 'string' || !p.name.trim() || (p.administrativeState != null && !['A', 'C'].includes(p.administrativeState)) ||
            typeof p.retrievedAt !== 'string' || !Number.isFinite(Date.parse(p.retrievedAt)) ||
            p.source !== `https://recherche-entreprises.api.gouv.fr/search?q=${p.siren}&per_page=25`) throw new Error(`${c.id} : identité fournisseur non rapprochée ou diffusion/provenance invalide.`);
        seenProfiles.add(p.siren);
      }
    }
    if (c.modificationConflicts != null && (!Array.isArray(c.modificationConflicts) || c.modificationConflicts.some(m => !m || typeof m.id !== 'string' || !Array.isArray(m.fields) || m.fields.some(f => typeof f !== 'string')))) throw new Error(`${c.id} : conflits de modifications invalides.`);
    if (c.initialConflicts != null && (!Array.isArray(c.initialConflicts) || c.initialConflicts.some(key => typeof key !== 'string'))) throw new Error(`${c.id} : conflits de versions invalides.`);
    if (c.history != null) {
      if (!Array.isArray(c.history) || c.history.filter(e => e?.kind === 'initial').length !== 1) throw new Error(`${c.id} : un historique exige exactement une entrée initiale.`);
      for (const event of c.history) {
        if (!event || !['initial', 'modification'].includes(event.kind)) throw new Error(`${c.id} : événement historique invalide.`);
        for (const key of ['id', 'supplierId']) if (event[key] != null && typeof event[key] !== 'string') throw new Error(`${c.id} : identifiant historique invalide.`);
        for (const key of ['amount', 'durationMonths']) if (event[key] != null && (typeof event[key] !== 'number' || !Number.isFinite(event[key]) || event[key] < 0)) throw new Error(`${c.id} : montant ou durée historique invalide.`);
        for (const key of ['date', 'publicationDate']) if (event[key] != null && (typeof event[key] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(event[key]) || !Number.isFinite(Date.parse(event[key])) || new Date(event[key]).toISOString().slice(0, 10) !== event[key])) throw new Error(`${c.id} : date historique invalide.`);
      }
    }
    if (c.initialAlternatives != null && (!Array.isArray(c.initialAlternatives) || c.initialAlternatives.some(a => !a || typeof a !== 'object' || (a.amount != null && (typeof a.amount !== 'number' || !Number.isFinite(a.amount) || a.amount < 0))))) throw new Error(`${c.id} : variantes initiales invalides.`);
    if (c.officialFinding === true && (c.dataStatus !== 'verified' || !safeSource(c.source) || !c.sourceReference)) {
      throw new Error(`${c.id} : un constat officiel exige une source vérifiée et un passage de référence.`);
    }
  }
  return data;
}

function selectContracts(contracts, { search = '', minimum = 0, minScore = 0, flagged = false, official = false, indicator = '', legal = '', noticeContext = '', sector = '', project = '', sort = 'score' } = {}) {
  const terms = normalize(search).trim().split(/\s+/).filter(Boolean);
  // Per-render caches only: no stale scores when data or cohort context changes.
  const scores = new Map();
  const increases = new Map();
  const scoreFor = c => { if (!scores.has(c)) scores.set(c, getVigilanceScore(c)); return scores.get(c); };
  const increaseFor = c => {
    if (!increases.has(c)) { const change = getAmountEvolution(c); increases.set(c, change.status === 'available' ? change.percentage : null); }
    return increases.get(c);
  };
  const collator = new Intl.Collator('fr', { sensitivity: 'base', numeric: true });
  return contracts.filter(c => {
    const projectText = c.project ? [c.project.title, c.project.basis] : [];
    const evidence = c.noticeEvidence;
    const noticeText = evidence ? [evidence.noticeUuid, evidence.lotReference, evidence.procedureId, evidence.procedureReference, evidence.procedureDescription, ...evidence.awardCriteria.map(a => [a.name, a.description, a.formula].join(' ')), ...evidence.justifications.map(j => j.text), ...evidence.references.map(r => r.id)] : [];
    const noticeMatch = !noticeContext || Boolean(evidence && (noticeContext === 'criteria' ? evidence.awardCriteria.length : noticeContext === 'explanation' ? evidence.procedureDescription || evidence.justifications.some(j => j.text) : noticeContext === 'correction' ? evidence.kind === 'correction' : noticeContext === 'ted' ? evidence.ted.length : false));
    const text = normalize([c.id, c.buyer, c.buyerSiret, c.supplier, c.description, c.procedure, c.cpv, c.contractId, c.lotId, c.noticeId, ...(c.supplierProfiles || []).map(p => p.name), c.consultation?.procedureReference, ...(c.consultation?.notices || []).map(n => n.id), ...(c.consultation?.lots || []).map(l => `${l.id || ''} ${l.description || ''}`), ...projectText, ...noticeText, ...(c.supplierIds || []).map(s => `${s.id} ${s.siren || ''}`)].join(' '));
    const citations = getLegalContext(c);
    const legalMatch = !legal || (legal === 'direct' ? c.directAward === true : legal === 'cited' ? citations.length > 0 : citations.some(item => item.article === legal));
    const sectorMatch = !sector || getSector(c).code === sector;
    const projectMatch = !project || (project === '@documented' ? Boolean(c.project) : c.project?.id === project);
    return terms.every(term => text.includes(term)) && noticeMatch && legalMatch && sectorMatch && projectMatch &&
      (minimum <= 0 || (c.amount != null && c.amount >= minimum)) && (minScore <= 0 || scoreFor(c) >= minScore) &&
      (!flagged || getIndicators(c).length > 0) && (!official || c.officialFinding === true) &&
      (!indicator || getIndicators(c).some(i => i.id === indicator));
  }).sort((a, b) => {
    const direction = ['score-asc', 'amount-asc', 'date-asc', 'publication-asc'].includes(sort) ? 1 : ['sector', 'buyer', 'supplier', 'offers'].includes(sort) ? 1 : -1;
    const field = sort.startsWith('score') ? 'score' : sort.startsWith('amount') ? 'amount' : sort.startsWith('date') ? 'date' : sort.startsWith('publication') ? 'publication' : sort === 'sector-desc' ? 'sector' : sort;
    const raw = c => field === 'score' ? scoreFor(c) : field === 'amount' ? c.amount : field === 'date' ? (c.date ? Date.parse(c.date) : null) :
      field === 'publication' ? (c.publicationDate ? Date.parse(c.publicationDate) : null) : field === 'sector' ? getSector(c).label : field === 'buyer' ? c.buyer : field === 'supplier' ? c.supplier :
      field === 'offers' ? c.offers : field === 'increase' ? increaseFor(c) : null;
    const av = raw(a), bv = raw(b);
    const nullOrder = av == null ? (bv == null ? 0 : 1) : bv == null ? -1 : 0;
    if (nullOrder) return nullOrder;
    if (field === 'sector' && av === 'Secteur non renseigné' && bv !== av) return 1;
    if (field === 'sector' && bv === 'Secteur non renseigné' && av !== bv) return -1;
    const comparison = typeof av === 'string' ? collator.compare(av, bv) : av === bv ? 0 : av > bv ? 1 : -1;
    return comparison * direction || (scoreFor(b) - scoreFor(a)) || collator.compare(a.id, b.id);
  });
}

// Everything from JSON is inserted as text, never as HTML.
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function renderNoticeEvidence(cell, c) {
  const e = c.noticeEvidence;
  function sourceLink(url, label) {
    const link = element('a', label); link.href = safeSource(url); link.target = '_blank'; link.rel = 'noopener noreferrer'; return link;
  }
  cell.append(element('h3', 'Avis complet · explications déclarées et critères'),
    element('p', `Version ${e.version || '—'} · UUID d’avis ${e.noticeUuid || '—'} · lot ${e.lotId || '—'} · référence locale du lot ${e.lotReference || '—'} · ${e.kind}. Une version/lot est un document, pas un contrat attribué unique.`),
    element('p', `Acheteurs résolus : ${e.buyers.map(b => `${b.name || '—'} (${b.siret || '—'})`).join(' / ')}. ${e.buyers.length > 1 ? 'Achat conjoint : ne pas affecter toutes les prestations ou dépenses à Tours.' : ''}`),
    element('p', `Cadre juridique publié : ${e.legalBasis || '—'} (directive/cadre général, pas justification d’une dérogation R2122).`));
  cell.append(element('h3', 'Texte déclaré par l’acheteur — portée globale de la procédure'), element('p', 'Ces textes peuvent concerner d’autres lots que celui affiché. Leur présence ne prouve ni leur applicabilité à ce lot, ni leur validité juridique. Aucun point supplémentaire.'));
  if (e.procedureDescription) cell.append(element('blockquote', e.procedureDescription), sourceLink(e.source, 'Source exacte · TenderingProcess/Description'));
  else cell.append(element('p', 'Description de procédure absente du champ repris : justification inconnue dans cet extrait, pas absence de justification.'));
  for (const j of e.justifications) {
    cell.append(element('p', `Déclaration structurée · liste ${j.category || '—'} · code ${j.code || '—'} · portée procédure entière.`));
    if (j.text) cell.append(element('blockquote', j.text));
    cell.append(element('small', j.path, 'provenance'));
  }
  cell.append(element('p', `Accélération explicitement déclarée : ${e.accelerated == null ? 'inconnue' : e.accelerated ? 'oui' : 'non'} · Relance déclarée : ${e.relaunch == null ? 'inconnue' : e.relaunch ? 'oui' : 'non'}. Une valeur false d’accélération n’est pas une justification d’exclusivité.`));
  cell.append(element('h3', `Critères d’attribution du lot ${e.lotId || 'inconnu'}`));
  if (!e.awardCriteria.length) cell.append(element('p', 'Critères non renseignés dans les champs repris. Ils peuvent figurer dans le règlement de consultation. Les critères de sélection des candidats ne sont pas substitués aux critères d’attribution.'));
  for (const a of e.awardCriteria) {
    const box = element('div', null, 'notice-criterion');
    box.append(element('p', `${a.type || 'Type non renseigné'} · ${a.name || a.description || a.formula || 'Libellé inconnu'}`));
    if (a.description && a.name) box.append(element('p', a.description));
    if (a.formula) box.append(element('p', `Méthode publiée : ${a.formula}`));
    if (!a.parameters.length) box.append(element('p', 'Pondération numérique inconnue dans ce champ.'));
    for (const p of a.parameters) box.append(element('p', `Valeur publiée : ${p.rawValue ?? '—'} · code de paramètre ${p.code || '—'} · liste ${p.codeList || '—'}. Codes et valeurs conservés, sans conversion arbitraire en pourcentage ni somme.`));
    box.append(element('small', a.path, 'provenance')); cell.append(box);
  }
  cell.append(element('p', 'Les critères et poids sont du contexte : un faible poids du prix n’est pas automatiquement suspect et ne rapporte aucun point.'));
  cell.append(element('h3', 'Publications, échéances et correspondance TED'), element('p', `Publication BOAMP : ${e.publicationDate || '—'} · Envoi déclaré : ${e.dispatchDate || '—'} ${e.dispatchTime || ''}. La date d’envoi et la date d’attribution ne sont pas utilisées comme publication initiale.`),
    element('p', `Échéance d’offre BOAMP du lot : ${e.deadline.date || '—'} ${e.deadline.time || ''}. Horaires et fuseaux conservés tels que publiés.`));
  for (const t of e.ted) {
    const line = element('p', `TED ${t.publicationNumber} · publication ${t.publicationDate || '—'} · version ${t.version || '—'} · ${t.versionMatches ? 'UUID et version concordants' : 'version différente : pas de substitution'} · échéance ${t.deadlineDate || '—'} ${t.deadlineTime || ''}. `);
    line.append(sourceLink(t.source, 'XML officiel'), element('span', ' · '));
    const local = element('a', 'XML téléchargé local'); local.href = t.localFile; local.setAttribute('download', ''); line.append(local); cell.append(line);
  }
  if (e.deadlineConflict) cell.append(element('p', 'Échéances divergentes entre sources : calcul exclu.'));
  if (e.linkedNoticeLots.length) {
    cell.append(element('h3', 'Chronologie partielle du même lot — références explicites'), element('p', 'Ces liens sont documentés, mais leur présence ne garantit pas que toutes les versions ou publications antérieures ont été retrouvées.'));
    for (const n of e.linkedNoticeLots) cell.append(element('p', `${n.relation} · ${n.noticeId} · ${n.lotId} · version ${n.version || '—'} · ${n.kind} · publication ${n.publicationDate || '—'} · échéance d’offre ${n.deadline || '—'}. ${n.basis}`), sourceLink(n.source, 'Avis explicitement relié'));
  }
  cell.append(element('h3', 'Références explicites et documents'));
  for (const r of e.references) {
    cell.append(element('p', `${r.kind} · ${r.id} · ${r.ambiguous ? 'référence ambiguë' : r.matchedNoticeIds.length ? 'avis BOAMP résolu : '+r.matchedNoticeIds.join(', ') : 'référence conservée, non résolue en avis BOAMP'}. ${r.path}`));
    if (r.tedSource) cell.append(sourceLink(r.tedSource, 'Avis TED antérieur explicitement cité et téléchargé'));
  }
  for (const n of e.sameProcedureNotices) cell.append(element('p', 'Même UUID de procédure, sans attribution automatique au lot : '), sourceLink(n.source, n.id));
  for (const d of e.documents) cell.append(element('p', 'Document du profil acheteur cité, non téléchargé : '), sourceLink(d.url, 'Accéder au document / profil'));
  cell.append(element('p', 'Aucune fusion avec DECP. Aucun montant, plafond ou version d’avis additionné. Le délai demeure non évaluable tant que la chaîne complète et la publication initiale pertinente ne sont pas établies.'));
}

function startExplorer() {
  const body = document.querySelector('#contracts');
  const status = document.querySelector('#status');
  const fileHelp = document.querySelector('#file-help');
  const controls = Object.fromEntries(['search', 'minimum', 'flagged', 'official', 'indicator', 'legal', 'notice-context', 'sort', 'sector', 'project', 'group-by', 'min-score'].map(id => [id, document.getElementById(id)]));
  const datasetSelect = document.querySelector('#dataset');
  const datasets = {
    tours: { path: 'data/tours-notices.json', coverage: 'data/tours-notices-coverage.json', note: 'Tours · avis complets 2025 et références liées hors période : 25 avis acheteur vérifié, 66 versions/lot, dont achats conjoints étiquetés. 25 lignes avec critères d’attribution ; textes de procédure et 2 rectificatifs conservés. XML TED rapprochés par UUID et version, pas par nom. Ce sont des documents, pas 66 contrats ou dépenses : aucun score de délai sans chaîne fiable.' },
    cities: { path: 'data/decp-cities.json', coverage: 'data/decp-cities-coverage.json', note: 'Six communes préchoisies : Rennes, Nantes, Bordeaux, Grenoble, Dijon et Tours (pas les métropoles). Notifications 2024–2025 : 1 865 lignes publiées, 1 270 groupes acheteur/identifiant, dont 172 ambigus exclus des calculs. 355 groupes avec modifications publiées. Cohorte non représentative, pas toutes les dépenses. 100 SIREN enrichis sur 703 identifiés : noms et état actuels, pas vérifiés à la date du contrat. Jeux séparés, aucune somme inter-sources.' },
    consultations: { path: 'data/consultations.json', coverage: 'data/consultations-coverage.json', note: '10 avis initiaux BOAMP du 3 février 2025, premiers identifiants parmi 200, sélectionnés avant calcul. Une correction et trois avis de résultat reliés explicitement. Lignes au niveau avis, pas contrats attribués ni dépenses. Chaînes non certifiées complètes : aucun score de délai dans cet extrait. Pas de téléchargement TED indépendant.' },
    decp: { path: 'data/decp-history.json', coverage: 'data/decp-coverage.json', note: 'Historique exploratoire de 24 mois : 2 594 contrats DECP de Paris et de l’Ardèche, notifiés en 2024–2025. Toutes les lignes retournées par la source pour ces deux SIRET ont été examinées ; cela ne garantit pas la publication de tous les achats réels. Paris a été choisi pour son volume, l’Ardèche pour la disponibilité de modifications : ce choix n’est pas représentatif. Les modifications peuvent être postérieures à 2025. Fournisseurs identifiés par SIRET ; trois dénominations du dossier parisien sont confirmées par l’Annuaire des entreprises. Les huit constats officiels se trouvent dans l’autre jeu.' },
    boamp: { path: 'data/contracts.json', coverage: 'data/coverage.json', note: '3 010 dossiers : 3 000 lots BOAMP échantillonnés parmi les publications de février–avril 2025, deux lots de Mauges et huit dossiers CRC documentés. Certains constats portent sur des ensembles de commandes, pas une attribution individuelle. Un constat ne s’étend pas aux autres achats d’une commune. Cet échantillon ne permet pas de calculer un historique de concurrence exhaustif.' }
  };
  const provenance = { verified: 'Documenté · source publique', unverified: 'À vérifier · piste de recherche', synthetic: 'Fictif · comparaison pédagogique' };
  const money = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
  const dateFormat = new Intl.DateTimeFormat('fr-FR', { timeZone: 'UTC' });
  let contracts = [];
  let loaded = false;
  let loadVersion = 0;
  let page = 0;
  const pageSize = 50;
  const pagination = document.querySelector('#pagination');
  const previous = document.querySelector('#previous');
  const next = document.querySelector('#next');
  const expanded = new Set();
  const viewport = document.querySelector('.table-wrap');
  const projectPanel = document.querySelector('#project-panel');
  let projectCatalog = new Map();

  function fillSelect(select, options) {
    const previousValue = select.value;
    select.replaceChildren(...options.map(([value, label]) => { const option = element('option', label); option.value = value; return option; }));
    select.value = options.some(([value]) => value === previousValue) ? previousValue : '';
  }
  function showProject(id) {
    controls.search.value = '';
    controls.minimum.value = '';
    controls['min-score'].value = '0';
    controls['notice-context'].value = '';
    controls.indicator.value = '';
    controls.legal.value = '';
    controls.sector.value = '';
    controls.flagged.checked = false;
    controls.official.checked = false;
    controls.project.value = id;
    controls['group-by'].value = id ? 'project' : '';
    page = 0;
    render();
    viewport.scrollTop = 0;
  }
  function renderProjectPanel() {
    projectPanel.replaceChildren();
    const project = projectCatalog.get(controls.project.value);
    projectPanel.hidden = !project;
    if (!project) return;
    projectPanel.append(element('h2', project.title), element('p', project.basis));
    const reference = element('a', 'Avis public de référence du dossier');
    reference.href = safeSource(project.source);
    reference.target = '_blank';
    reference.rel = 'noopener noreferrer';
    projectPanel.append(reference);
    const list = element('ol', null, 'evidence-list');
    (project.evidence || []).forEach(evidence => {
      const item = element('li');
      const link = element('a', `${evidence.date} — ${evidence.label}`);
      link.href = safeSource(evidence.source);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      item.append(link, element('span', ` · ${evidence.type}. ${evidence.description}`));
      list.append(item);
    });
    projectPanel.append(list, element('p', 'Ces éléments documentaires ne rapportent pas de points supplémentaires et ne constituent pas un constat officiel. Aucun montant ni score de projet n’est additionné.'));
    const clear = element('button', 'Revenir à tous les dossiers', 'clear-group');
    clear.type = 'button';
    clear.addEventListener('click', () => showProject(''));
    projectPanel.append(clear);
  }

  function render() {
    if (!loaded) return;
    const minimum = Math.max(0, Number(controls.minimum.value) || 0);
    const filtered = selectContracts(contracts, { search: controls.search.value, minimum, minScore: Number(controls['min-score'].value) || 0, flagged: controls.flagged.checked, official: controls.official.checked, indicator: controls.indicator.value, legal: controls.legal.value, noticeContext: controls['notice-context'].value, sector: controls.sector.value, project: controls.project.value, sort: controls.sort.value });
    const arrangement = arrangeGroups(filtered, controls['group-by'].value);
    const visible = arrangement.rows;
    renderProjectPanel();
    const pageCount = Math.max(1, Math.ceil(visible.length / pageSize));
    page = Math.min(page, pageCount - 1);
    const pageRows = visible.slice(page * pageSize, (page + 1) * pageSize);
    const fragment = document.createDocumentFragment();
    pageRows.forEach((c, index) => {
      const indicators = getIndicators(c);
      if (controls['group-by'].value) {
        const info = groupInfo(c, controls['group-by'].value);
        const preceding = visible[page * pageSize + index - 1];
        if (index === 0 || groupInfo(preceding, controls['group-by'].value).key !== info.key) {
          const group = arrangement.groups.get(info.key);
          const header = element('tr', null, 'group-row');
          const headerCell = element('td', `${group.label} · ${group.contracts.length} résultat(s) filtré(s)${index === 0 && preceding && groupInfo(preceding, controls['group-by'].value).key === info.key ? ' · suite' : ''}`);
          headerCell.colSpan = 9;
          if (controls['group-by'].value === 'project' && c.project) {
            const link = element('button', 'Voir le dossier et ses sources', 'group-link');
            link.type = 'button';
            link.addEventListener('click', () => showProject(c.project.id));
            headerCell.append(element('span', ' · '), link);
          }
          header.append(headerCell);
          fragment.append(header);
        }
      }
      const row = element('tr', null, 'contract-row');
      const supplierCell = element('td', c.supplier || '—');
      for (const p of c.supplierProfiles || []) supplierCell.append(element('small', `${p.name} · nom actuel (${p.retrievedAt.slice(0, 10)}), pas historique`, 'provenance'));
      const dateCell = element('td', c.date ? dateFormat.format(new Date(c.date)) : c.noticeEvidence ? c.publicationDate || '—' : '—');
      if (c.noticeEvidence) dateCell.append(element('small', 'Publication BOAMP', 'provenance'));
      row.append(dateCell, element('td', c.buyer), supplierCell);
      const objectCell = element('td');
      const button = element('button', c.description, 'row-toggle');
      button.type = 'button';
      button.setAttribute('aria-expanded', String(expanded.has(c.id)));
      button.setAttribute('aria-controls', `detail-${index}`);
      objectCell.append(button, element('small', provenance[c.dataStatus], 'provenance'));
      if (c.project) {
        const projectLink = element('button', `Projet : ${c.project.title}`, 'group-link');
        projectLink.type = 'button';
        projectLink.addEventListener('click', event => { event.stopPropagation(); showProject(c.project.id); });
        objectCell.append(element('br'), projectLink);
      }
      if (c.noticeEvidence) objectCell.append(element('small', `Avis ${c.noticeId} · ${c.lotId || 'lot inconnu'} · réf. locale ${c.noticeEvidence.lotReference || '—'}`, 'provenance'));
      const legalContext = getLegalContext(c);
      if (legalContext.length) objectCell.append(element('small', `Contexte · ${[...new Set(legalContext.map(item => item.article))].join(', ')} cité · aucun point ajouté`, 'provenance'));
      if (c.initialConflicts?.length) objectCell.append(element('small', isAmbiguousCityContract(c) ? 'Identifiant / versions ambigus · calculs exclus' : 'Valeurs initiales divergentes · nouveaux calculs exclus', 'provenance'));
      if (c.modificationConflicts?.length) objectCell.append(element('small', 'Versions de modifications contradictoires', 'provenance'));
      if ([c.amount, c.offers, c.durationMonths, c.directAward].some(value => value == null)) {
        objectCell.append(element('small', 'Données partielles · consulter les détails', 'provenance'));
      }
      if (c.findingScope) objectCell.append(element('small', c.findingScope === 'aggregate' ? 'Constat sur un ensemble de commandes' : 'Constat rattaché au contrat décrit', 'provenance'));
      const amountPrefix = { 'at-least': '≥ ', 'more-than': '> ', approximate: '≈ ' }[c.amountQualifier] || '';
      const sector = getSector(c);
      const sectorCell = element('td', sector.label);
      sectorCell.append(element('small', c.cpv || 'CPV inconnu', 'provenance'));
      row.append(objectCell, sectorCell, element('td', c.amount == null ? '—' : amountPrefix + money.format(c.amount), 'numeric'), element('td', c.offers ?? '—', 'numeric'));
      const badges = element('td');
      if (indicators.length) indicators.forEach(i => {
        const badge = element('span', `${i.label} · ${i.weight} pts · ${i.severityLabel.toLocaleLowerCase('fr')}`, `badge severity-${i.severity}${i.id === 'official-finding' ? ' official' : ''}`);
        badge.title = `Niveau de vigilance ${i.severityLabel.toLocaleLowerCase('fr')} ; poids brut, non additionné aux autres signaux de la même famille. ${i.explanation}`;
        badges.append(badge);
      });
      else badges.append(element('span', c.dataStatus === 'unverified' ? 'Données à compléter' : 'Aucun indicateur déclenché', 'muted'));
      const scoreValue = getVigilanceScore(c);
      const level = scoreLevel(scoreValue, hasIncompleteData(c));
      const score = element('td', null, 'numeric');
      const documentaryOnly = Boolean(c.noticeEvidence && getBiddingPeriod(c).status !== 'available' && scoreValue === 0);
      const chip = element('span', documentaryOnly ? 'Non évalué' : `${scoreValue} / 100`, `score-chip level-${level.id}`);
      chip.title = `${level.label} — indice éditorial, pas probabilité ni gravité juridique.`;
      score.append(chip, element('small', documentaryOnly ? 'Contexte documentaire' : level.label, 'provenance'));
      score.setAttribute('aria-label', documentaryOnly ? 'Avis documentaire : délai non évaluable, pas une note zéro.' : `Indice de vigilance : ${scoreValue} sur 100. ${level.label}.`);
      row.append(badges, score);
      const detail = element('tr', null, 'detail-row');
      detail.id = `detail-${index}`;
      detail.hidden = !expanded.has(c.id);
      const cell = element('td');
      cell.colSpan = 9;
      cell.append(element('p', `${provenance[c.dataStatus]} · Référence : ${c.id}`), element('p', `Procédure : ${c.procedure || 'non renseignée'} · Durée : ${c.durationMonths == null ? 'non renseignée' : `${c.durationMonths} mois`}`));
      if (c.findingScope) cell.append(element('p', c.findingScope === 'aggregate' ? 'Périmètre : ensemble de commandes ou de prestations examiné par la CRC, pas attribution individuelle. Ce constat n’est pas étendu aux autres marchés de l’acheteur ou du fournisseur.' : 'Périmètre : contrat décrit dans ce dossier. Ce constat n’est pas étendu aux autres marchés de l’acheteur ou du fournisseur.'));
      if (c.dateNote) cell.append(element('p', `Date : ${c.dateNote}`));
      if (c.amountBasis) cell.append(element('p', `Périmètre du montant : ${c.amountBasis}`));
      if (c.notes) cell.append(element('p', c.notes));
      cell.append(element('p', `Identifiants — Acheteur SIRET : ${c.buyerSiret || '—'} · Contrat : ${c.contractId || '—'} · Lot : ${c.lotId || '—'} · CPV : ${c.cpv || '—'}`));
      if (c.noticeId || c.publicationDate) cell.append(element('p', `Avis : ${c.noticeId || '—'} · Publication : ${c.publicationDate || '—'}`));
      if (c.supplierIds?.length) cell.append(element('p', `Titulaires : ${c.supplierIds.map(s => `${s.identifierType || 'Identifiant'} ${s.id}${s.siren ? ` · SIREN ${s.siren}` : ''}`).join(' / ')}`));
      if (c.directAward === true || legalContext.length) {
        cell.append(element('h3', 'Fondement juridique déclaré — contexte, pas indicateur'), element('p', 'Une citation ne prouve ni que les conditions légales sont remplies, ni une irrégularité. Une seule offre reçue ne démontre pas une exclusivité. Aucun point ajouté ; aucune déduction sur les autres contrats.'));
        if (!legalContext.length) cell.append(element('p', 'Article R2122 non repéré dans l’objet ou la procédure importés. Justification inconnue dans cet extrait, pas absence de justification.'));
        if (c.initialConflicts?.length) cell.append(element('p', 'Versions initiales divergentes : contexte du texte affiché seulement, pas validation du fondement. Les variantes restent à examiner dans la source.'));
        for (const context of legalContext) {
          cell.append(element('p', `${context.article} · ${context.label} · citation exacte : « ${context.citation} »`), element('blockquote', context.excerpt));
          const link = element('a', `Source du texte publié (${context.field === 'description' ? 'objet' : 'procédure'})`);
          link.href = safeSource(context.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          cell.append(link);
        }
      }
      if (c.identifierNote) cell.append(element('p', c.identifierNote));
      if (c.supplierProfiles?.length) {
        cell.append(element('h3', 'Identité publique actuelle — pas historique'), element('p', 'Rapprochement par SIREN dérivé d’un identifiant français explicitement typé. Nom et état de l’unité légale observés lors de la récupération, pas ceux de chaque établissement ni ceux à la date du marché. Aucun point pour le nom ou l’état ; aucun lien entre sociétés déduit.'));
        for (const p of c.supplierProfiles) {
          const state = p.administrativeState === 'A' ? 'active' : p.administrativeState === 'C' ? 'cessée' : 'inconnu';
          const paragraph = element('p', `${p.name} · SIREN ${p.siren} · état actuel de l’unité légale : ${state} · photographie ${p.retrievedAt}. `);
          const link = element('a', 'Annuaire des entreprises — source exacte');
          link.href = safeSource(p.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          paragraph.append(link); cell.append(paragraph);
        }
      } else if (c.cohortId === CITIES_COHORT) cell.append(element('p', 'Identité actuelle non enrichie dans cet extrait : hors échantillon de 100 SIREN, identité ambiguë ou information non disponible. Le nom historique reste inconnu.'));
      if (c.executionModalities || c.techniques) cell.append(element('p', `Modalités publiées : ${c.executionModalities || '—'} · Techniques : ${c.techniques || '—'}. Montants déclarés, pas dépenses constatées ; ne pas additionner les plafonds d’accord-cadre.`));
      if (c.frameworkId) cell.append(element('p', `Accord-cadre parent cité dans la source : ${c.frameworkId}. Un marché subséquent ne constitue pas un projet distinct par simple déduction.`));
      if (c.project) cell.append(element('p', `Projet documenté : ${c.project.title}. ${c.project.basis}`));
      if (isAmbiguousCityContract(c)) cell.append(element('p', 'Calculs exclus : groupe de versions / identifiant ambigu. Le zéro affiché est une absence de calcul, pas une absence de vigilance. Les variantes et événements sont conservés sans les additionner.'));
      const breakdown = getScoreBreakdown(c);
      if (!documentaryOnly) cell.append(element('p', `Calcul v${SCORE_VERSION} : concurrence ${breakdown.competition} (maximum des signaux), exécution/durée ${breakdown.execution} (maximum), constat officiel ${breakdown.official}. Total plafonné : ${breakdown.score}/100. Aucun point pour le montant seul ni pour l’appartenance à un projet.`));
      if (c.noticeEvidence) renderNoticeEvidence(cell, c);
      if (c.consultation) {
        const timeline = c.consultation;
        cell.append(element('h3', 'Consultation : publications et versions'), element('p', `Référence interne : ${timeline.procedureReference || '—'} · Procédure UUID : ${timeline.procedureId || '—'} · Lot analysé : ${timeline.lotId || '—'}. Une ligne représente un avis, pas une attribution.`));
        const list = element('ol');
        for (const n of [...timeline.notices, ...(timeline.matchedAwards || [])]) {
          const item = element('li');
          const link = element('a', `${n.id} · ${n.kind} · état ${n.publicationState || '—'} · version ${n.version || '—'} · publication ${n.publicationDate || '—'}`);
          link.href = safeSource(n.source); link.target = '_blank'; link.rel = 'noopener noreferrer';
          item.append(link, element('span', ` · Échéance publiée : ${n.deadline || '—'} · Procédure : ${n.procedureType || '—'} · Accélérée : ${n.accelerated == null ? 'inconnu' : n.accelerated ? 'oui' : 'non'} · Références antérieures : ${(n.previousNoticeIds || []).join(', ') || '—'}`));
          if (n.correctionText) item.append(element('p', n.correctionText));
          list.append(item);
        }
        for (const lot of timeline.lots || []) cell.append(element('p', `Lot publié : ${lot.id || 'identifiant inconnu'} · ${lot.description || '—'} · CPV ${(lot.cpv || []).join(', ') || '—'} · échéance brute ${lot.deadline || '—'}. Aucun score par lot sans calendrier vérifié.`));
        const period = getBiddingPeriod(c);
        cell.append(list, element('p', period.status === 'available' ? `Délai : ${period.days.toFixed(2)} jours (borne haute), dernière échéance ${period.deadline}.` : `Délai non évaluable : ${period.reason}`));
        (timeline.exclusions || []).forEach(reason => cell.append(element('p', reason)));
        cell.append(element('p', 'Un résultat relié à cet avis ne prouve pas une correspondance de chaque lot ; aucun montant, titulaire ou constat n’est transféré.'));
      }
      if (c.dataFamily === 'decp') {
        cell.append(element('h3', 'Historique publié du contrat'));
        cell.append(element('p', `Forme du prix : ${c.priceForm || '—'} · Type : ${c.priceType || '—'}. Montants déclarés, pas paiements constatés.`));
        if (c.initialConflicts?.length) {
          cell.append(element('p', `Versions initiales contradictoires (${c.initialConflicts.join(', ')}). Aucune chronologie n’est inférée à partir de ces différences.`));
          const alternatives = element('ul');
          (c.initialAlternatives || []).forEach((a, n) => {
            const item = element('li', `Variante initiale ${n + 1} : ${a.amount == null ? 'montant inconnu' : money.format(a.amount)} — ce n’est pas un avenant daté.`);
            if (c.cohortId === CITIES_COHORT) item.append(element('p', `Notification : ${a.date || '—'} · Publication : ${a.publicationDate || '—'} · CPV : ${a.cpv || '—'} · Offres : ${a.offers ?? '—'} · Procédure : ${a.procedure || '—'} · Titulaires : ${Array.isArray(a.supplierIds) ? a.supplierIds.map(s => s.id).join(' / ') || '—' : '—'}`), element('p', a.description || 'Objet inconnu dans cette variante.'));
            alternatives.append(item);
          });
          cell.append(alternatives);
        }
        if (c.modificationConflicts?.length) cell.append(element('p', `Modifications contradictoires : ${c.modificationConflicts.map(m => `${m.id} (${m.fields.join(', ')})`).join(' ; ')}. Pas de calcul d’évolution.`));
        if (c.history?.length) {
          const historyTable = element('table', null, 'history-table');
          historyTable.append(element('caption', 'Versions publiées disponibles — absence d’avenant publié ≠ absence de modification réelle.'));
          const head = element('thead');
          const heading = element('tr');
          ['Événement', 'Notification', 'Publication', 'Montant déclaré'].forEach(label => { const th = element('th', label); th.scope = 'col'; heading.append(th); });
          head.append(heading);
          const entries = element('tbody');
          c.history.forEach(event => {
            const entry = element('tr');
            entry.append(element('td', event.kind === 'initial' ? 'Attribution initiale' : `Modification ${event.id || '—'}`), element('td', event.date || '—'), element('td', event.publicationDate || '—'), element('td', event.amount == null ? '—' : money.format(event.amount)));
            entries.append(entry);
          });
          historyTable.append(head, entries);
          cell.append(historyTable);
        }
        const evolution = getAmountEvolution(c);
        cell.append(element('p', evolution.status === 'available' ? `Évolution déclarée analysable : +${money.format(evolution.delta)} (+${evolution.percentage.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %), de ${money.format(evolution.initialAmount)} à ${money.format(evolution.revisedAmount)}, au ${evolution.date}. Les quantités ou le périmètre peuvent avoir changé ; consulter la source.` : `Calcul de hausse indisponible : ${evolution.reason}`));
        const supplierContext = c.supplierContext;
        if (supplierContext) cell.append(element('p', `Titulaire unique identifié : SIREN ${getSupplierIdentity(c)}. Même acheteur/CPV ${supplierContext.cpvGroup}, 2024–2025 : ${supplierContext.wins}/${supplierContext.known} contrats au titulaire connu, sur ${supplierContext.total} contrats admissibles (${Math.round(supplierContext.coverage * 100)} % de couverture) ; ${supplierContext.directCount} attributions sans concurrence d’au moins 100 k€ à ce titulaire. ${supplierContext.sufficient ? 'Effectif suffisant pour examiner la concentration.' : 'Concentration non calculable : effectif ou couverture insuffisant.'} Les statistiques ne changent pas avec les filtres.`));
        const context = c.competitionContext;
        cell.append(element('p', context ? `Contexte rétrospectif ${context.start}–${context.end}, même acheteur et CPV ${context.cpvGroup} : ${context.single} contrats à une offre / ${context.known} au nombre connu, sur ${context.total} contrats concurrentiels admissibles (${Math.round(context.coverage * 100)} % de couverture). ${context.sufficient ? 'Seuils de couverture atteints.' : 'Effectif ou couverture insuffisant : aucun indicateur de répétition.'} Calcul sur toute la cohorte, inchangé par vos filtres.` : 'Concurrence répétée non calculable : procédure non explicitement concurrentielle, conflit de versions, identifiant manquant ou contrat hors cohorte.'));
      }
      if (indicators.length) {
        const list = element('ul');
        indicators.forEach(i => list.append(element('li', `${i.label} — ${i.severityLabel}, poids brut ${i.weight}, famille ${i.family}. ${i.explanation}`)));
        cell.append(list);
      } else cell.append(element('p', 'Aucune des règles disponibles ne se déclenche avec les données disponibles. Les valeurs inconnues ne valent pas absence de risque.'));
      if (c.sourceReference) cell.append(element('p', `Passage source : ${c.sourceReference}`));
      if (safeSource(c.source)) {
        const link = element('a', c.sourceLabel || 'Consulter la source originale');
        link.href = safeSource(c.source);
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        cell.append(link);
      } else cell.append(element('p', c.dataStatus === 'synthetic' ? 'Source : aucune, exemple entièrement fictif.' : 'Source originale non fournie : cette piste reste à vérifier.'));
      for (const [key, label] of [['reportUrl', 'Rapport officiel original'], ['responseLink', 'Réponse officielle de l’organisme contrôlé'], ['supplierNameSource', 'Dénomination du fournisseur — Annuaire des entreprises']]) {
        if (!safeSource(c[key])) continue;
        const paragraph = element('p');
        const link = element('a', label);
        link.href = safeSource(c[key]);
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        paragraph.append(link);
        cell.append(paragraph);
      }
      detail.append(cell);
      function toggle() {
        if (expanded.has(c.id)) expanded.delete(c.id); else expanded.add(c.id);
        detail.hidden = !expanded.has(c.id);
        button.setAttribute('aria-expanded', String(!detail.hidden));
      }
      button.addEventListener('click', event => { event.stopPropagation(); toggle(); });
      row.addEventListener('click', () => { if (!window.getSelection()?.toString()) toggle(); });
      fragment.append(row, detail);
    });
    if (!visible.length) {
      const row = element('tr');
      const cell = element('td', 'Aucun résultat. Essayez de réduire le montant minimum ou de modifier les filtres.');
      cell.colSpan = 9;
      row.append(cell);
      fragment.append(row);
    }
    body.replaceChildren(fragment);
    status.textContent = `${visible.length} / ${contracts.length} résultats · ${visible.filter(c => getIndicators(c).length).length} signalés · Lignes ${visible.length ? page * pageSize + 1 : 0}–${page * pageSize + pageRows.length} · Indice de vigilance : outil de tri uniquement.`;
    pagination.hidden = visible.length <= pageSize;
    previous.disabled = page === 0;
    next.disabled = page >= pageCount - 1;
    document.querySelector('#page-status').textContent = `Page ${page + 1} / ${pageCount} · ${pageSize} lignes par page`;
  }
  function accept(data) {
    contracts = prepareContracts(data);
    const sectors = [...new Map(contracts.map(c => { const s = getSector(c); return [s.code, s]; })).values()].sort((a, b) => a.code === 'unknown' ? 1 : b.code === 'unknown' ? -1 : a.label.localeCompare(b.label, 'fr'));
    fillSelect(controls.sector, [['', 'Tous les secteurs'], ...sectors.map(s => [s.code, `${s.code === 'unknown' ? '' : s.code + ' · '}${s.label}`])]);
    projectCatalog = new Map(contracts.filter(c => c.project).map(c => [c.project.id, c.project]));
    fillSelect(controls.project, [['', 'Tous les dossiers'], ...(projectCatalog.size ? [['@documented', 'Projets documentés uniquement']] : []), ...[...projectCatalog.values()].map(p => [p.id, p.title])]);
    controls.project.disabled = projectCatalog.size === 0;
    loaded = true;
    page = 0;
    const missing = key => contracts.filter(c => c[key] == null).length;
    const conflictCount = contracts.filter(c => c.initialConflicts?.length).length;
    const withMods = contracts.filter(c => c.history?.some(event => event.kind === 'modification')).length;
    const enrichedCount = contracts.filter(c => c.supplierProfiles?.length).length;
    document.querySelector('#completeness').textContent = `Dans le fichier chargé : ${missing('amount')} montants, ${missing('offers')} nombres d’offres et ${missing('durationMonths')} durées non renseignés sur ${contracts.length} dossiers. ${conflictCount} groupes aux valeurs initiales divergentes ; ${withMods} historiques comportant une modification publiée. ${enrichedCount ? `${enrichedCount} dossiers avec un nom public actuel enrichi (pas historique). ` : ''}Les constats officiels ne font pas l’objet d’une recherche automatique exhaustive.`;
    expanded.clear();
    render();
  }
  function fail(error) {
    loaded = false;
    contracts = [];
    body.replaceChildren();
    pagination.hidden = true;
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    document.querySelector('#completeness').textContent = '';
    status.textContent = `Impossible de charger les données : ${error.message}`;
    fileHelp.hidden = false;
  }
  Object.values(controls).forEach(control => control.addEventListener('input', () => { page = 0; render(); viewport.scrollTop = 0; }));
  previous.addEventListener('click', () => { if (page > 0) { page--; render(); viewport.scrollTop = 0; } });
  next.addEventListener('click', () => { page++; render(); viewport.scrollTop = 0; });
  document.querySelector('#file').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    const version = ++loadVersion;
    try {
      const data = JSON.parse(await file.text());
      if (version === loadVersion) {
        accept(data);
        document.querySelector('#dataset-note').textContent = `Fichier local chargé : ${file.name}. Les statistiques décrivent ce fichier ; elles ne prouvent pas son exhaustivité. Utilisez le sélecteur de jeu pour recharger un jeu fourni.`;
        document.querySelector('#coverage-link').hidden = true;
      }
    }
    catch (error) { if (version === loadVersion) fail(error); }
  });
  async function loadDataset() {
    const selected = datasets[datasetSelect.value];
    const version = ++loadVersion;
    loaded = false;
    contracts = [];
    body.replaceChildren();
    pagination.hidden = true;
    document.querySelector('#completeness').textContent = '';
    document.querySelector('#dataset-note').textContent = selected.note;
    document.querySelector('#coverage-link').href = selected.coverage;
    document.querySelector('#coverage-link').hidden = false;
    document.querySelector('#file-path').textContent = selected.path;
    document.querySelector('#file').value = '';
    fileHelp.hidden = location.protocol !== 'file:';
    controls.search.value = '';
    controls.minimum.value = '';
    controls['notice-context'].value = '';
    controls.indicator.value = '';
    controls.legal.value = '';
    controls.sector.value = '';
    controls.project.value = '';
    controls['group-by'].value = '';
    controls['min-score'].value = '0';
    projectPanel.hidden = true;
    projectPanel.replaceChildren();
    viewport.scrollTop = 0;
    controls.flagged.checked = false;
    controls.official.checked = false;
    status.textContent = 'Chargement des données…';
    try {
      const response = await fetch(selected.path);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (version === loadVersion) accept(data);
    } catch (error) { if (version === loadVersion) fail(error); }
  }
  datasetSelect.addEventListener('change', loadDataset);
  loadDataset();
}

if (typeof document !== 'undefined') startExplorer();
