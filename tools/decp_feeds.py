"""Reconcile DECP cohort records with the buyers' own feeds (data/decp-feeds-raw.json.gz).

Shared by tools/import-decp-cities.py and tools/import-decp-paris-ardeche.py, applied after
their own normalisation. Rules (research/france-cross-dataset-check.md):

- Every source's initial amount is kept in `amountSources`; nothing is summed.
- Amounts from 0.01 to 10 EUR are placeholders: kept as published, never used as money.
- When strictly more publication routes give one positive amount than any other (at least two;
  an AWS profile and its scraped copy are one route), that amount is shown, noted as `majority`.
  Routes are all the buyer's own declarations, so a majority is corroboration, not proof.
- Otherwise the amount shown is the buyer feed's when it gives exactly one positive value, otherwise the
  Ministry's positive value; a declared zero is shown only when no source gives a positive amount;
  several disagreeing feed values without the Ministry's leave it unknown.
- `verification.status`: notice-checked (curated award-notice linkage), sources-agree,
  sources-disagree, or single-source. Disagreement keeps `amountRange` for threshold checks.
- Positive offer counts that differ between the Ministry row and the buyer feed make the count
  unknown, both values kept in `offersConflict` (a zero count is already unusable, not a conflict).
- A feed row with the same identifier, date, amount and object as a record but another holder is a
  co-holder the Ministry table dropped (three holder slots): it is added to `supplierIds` with its source.
- "Possibly the same contract" clusters are settled with route evidence (resolve_duplicate_clusters).
- A feed contract that matches no record by id+date+holder, holder+amount+date,
  holder+date+object, or (holderless) amount+date is added as a single-source record.
"""
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDS = ROOT / 'data/decp-feeds-raw.json.gz'
PLACEHOLDER_MAX = 10
SCRAPED = 'scrap_marches-publics.info'
FEED_LABELS = {
    'atexo_maximilien': 'Ville de Paris — profil acheteur (Atexo / Maximilien)',
    'atexo_nantes_metro': 'Nantes — profil acheteur (Atexo)',
    'megalis_bretagne': 'Rennes — profil acheteur (Mégalis Bretagne)',
    'aws_marches-publics.info': 'Profil acheteur AWS (marches-publics.info)',
    SCRAPED: 'Profil acheteur AWS — copie collectée par decp.info',
    'pes_marche_2024': 'Export comptable PES Marché',
    'pes_marche_legacy': 'Export comptable PES Marché (ancien)',
    'aife_dume': 'AIFE / DUME',
    'atexo_mp_aquitaine': 'Profil acheteur Atexo (Marchés publics Aquitaine)',
    'decp_colmo': 'Saisie consolidée decp.info',
    'portal_nantes': 'Ville de Nantes — portail open data (marchés conclus)',
    'portal_bordeaux': 'Bordeaux Métropole — datahub (marchés publics depuis 2024)',
}
PORTALS = ROOT / 'data/city-portals-raw.json.gz'


def load(path=FEEDS, portals=None):
    """Buyer feeds, optionally with the buyers' own open-data contract lists as further routes."""
    feed = json.loads(gzip.decompress(Path(path).read_bytes()))
    if portals:
        extra = json.loads(gzip.decompress(Path(portals).read_bytes()))
        start, end = feed['window']  # the cohorts' notification window, as for the feed extraction
        feed['records'] = feed['records'] + [r for r in extra['records'] if r.get('dateNotification') and start <= r['dateNotification'] <= end]
        feed['portals'] = extra['sources']
    return feed


def money(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return round(v, 2) if v >= 0 else None


def usable(value):
    return value is not None and (value == 0 or value > PLACEHOLDER_MAX)


def placeholder(value):
    return value is not None and 0 < value <= PLACEHOLDER_MAX


def words(text):
    return re.sub(r'\W+', ' ', str(text or '').lower()).strip()


def holders(record):
    return {s['id'] for s in record.get('supplierIds') or []}


def ministry_amounts(record):
    """Initial amounts the Ministry published for this record (both rows of a conflicting pair)."""
    if 'amount' in (record.get('initialConflicts') or []):
        return sorted({a.get('amount') for a in record.get('initialAlternatives') or [] if a.get('amount') is not None})
    return [record['amount']] if record.get('amount') is not None else []


def feed_contracts(feed, buyers):
    """Feed contracts (one initial row each, with that contract's modification rows)."""
    groups = defaultdict(list)
    for row in feed['records']:
        if row['acheteur_id'] in buyers:
            groups[(row['sourceDataset'], row['uid'], row['titulaire_id'])].append(row)
    contracts = []
    for rows in groups.values():
        initials = [r for r in rows if r['modification_id'] in (0, None)]
        mods = sorted((r for r in rows if r['modification_id'] not in (0, None)), key=lambda r: r['modification_id'])
        for initial in initials:
            # Several initial rows under one uid+holder cannot be told apart: no modification is attached.
            contracts.append({'initial': initial, 'mods': mods if len(initials) == 1 else []})
    return contracts


class Index:
    def __init__(self, records):
        self.by_id, self.by_amount, self.by_object, self.by_blind = (defaultdict(list) for _ in range(4))
        for r in records:
            date = r.get('date') or next((a.get('date') for a in r.get('initialAlternatives') or [] if a.get('date')), None)
            self.by_id[(r['buyerSiret'], r['contractId'], date)].append(r)
            for amount in ministry_amounts(r) or [None]:
                self.by_blind[(r['buyerSiret'], amount, date)].append(r)
                for h in holders(r):
                    self.by_amount[(r['buyerSiret'], h, amount, date)].append(r)
            for h in holders(r):
                self.by_object[(r['buyerSiret'], h, date, words(r.get('description')))].append(r)

    def match(self, row):
        """(record, how) for a feed initial row; (None, reason) when absent or ambiguous."""
        buyer, date, holder, amount = row['acheteur_id'], row['dateNotification'], row['titulaire_id'], money(row['montant'])
        same_id = self.by_id.get((buyer, row['id'], date), [])
        if holder:
            hits = [r for r in same_id if holder in holders(r)]
            if len(hits) > 1:
                hits = [r for r in hits if amount in ministry_amounts(r)]
            if len(hits) == 1:
                return hits[0], 'id-date-holder'
            if len(hits) > 1:
                return None, 'ambiguous'
            for index, how in [(self.by_amount, 'holder-amount-date'), (self.by_object, 'holder-date-object')]:
                key = (buyer, holder, amount, date) if how == 'holder-amount-date' else (buyer, holder, date, words(row['objet']))
                found = {r['id']: r for r in index.get(key, [])}
                if len(found) == 1:
                    return next(iter(found.values())), how
                if len(found) > 1:
                    return None, 'ambiguous'
            if same_id:
                # Same contract with a holder the Ministry table dropped (it carries three holder slots),
                # or a different contract under a reused identifier.
                same = [r for r in same_id if amount in ministry_amounts(r) and words(r.get('description')) == words(row['objet'])]
                if len(same) == 1:
                    return same[0], 'co-holder'
                if not any(amount in ministry_amounts(r) or words(r.get('description')) == words(row['objet']) for r in same_id):
                    return None, 'absent'
                return None, 'same-id-other-holder'
            return None, 'absent'
        found = {r['id']: r for r in self.by_blind.get((buyer, amount, date), [])}
        if len(found) == 1:
            return next(iter(found.values())), 'amount-date-no-holder'
        return None, 'ambiguous' if found or same_id else 'absent'


def source_entry(row):
    return {'source': row['sourceDataset'], 'label': FEED_LABELS.get(row['sourceDataset'], row['sourceDataset']),
            'id': row['id'], 'amount': money(row['montant']), 'consolidatorFlag': row.get('montant_anomalie')}


def decide(ministry, feed_values):
    """Amount shown, by the documented rule; None when it cannot be chosen.

    Positive amounts win over a declared zero (a zero beside a positive value would hide money);
    the buyer feed wins over the Ministry when it gives exactly one positive value."""
    positive = lambda values: sorted({v for v in values if usable(v) and v > 0})
    feed_pos, ministry_pos = positive(feed_values), positive(ministry)
    if len(feed_pos) == 1:
        return feed_pos[0]
    if len(feed_pos) > 1:
        common = [v for v in ministry_pos if v in feed_pos]
        return common[0] if len(common) == 1 else None
    if len(ministry_pos) == 1:
        return ministry_pos[0]
    if ministry_pos:
        return None
    return 0.0 if 0 in [*feed_values, *ministry] else None


def family(source):
    """Publication route: a scraped copy of an AWS buyer profile is the same route as the profile."""
    return 'aws' if source in ('aws_marches-publics.info', SCRAPED) else source


def majority(sources):
    """The positive amount published by strictly more routes than any other, if at least two."""
    support, given = defaultdict(set), defaultdict(set)
    for s in sources:
        if usable(s['amount']) and s['amount'] > 0:
            given[family(s['source'])].add(s['amount'])
    # A route that publishes several amounts for one contract contradicts itself and does not vote.
    for route, amounts in given.items():
        if len(amounts) == 1:
            support[next(iter(amounts))].add(route)
    ranked = sorted(support.items(), key=lambda kv: -len(kv[1]))
    if len(ranked) > 1 and len(ranked[0][1]) >= 2 and len(ranked[0][1]) > len(ranked[1][1]):
        return ranked[0][0], len(ranked[0][1]), len(given)
    return None


def reconcile_record(record, matches):
    ministry = ministry_amounts(record)
    rows = [m for m in matches if m['sourceDataset'] != SCRAPED] or matches
    feed_values = [money(m['montant']) for m in rows]
    sources = [{'source': 'ministry', 'label': 'Ministère — jeu « decp-2022-marches-valides »', 'id': record['contractId'], 'amount': a} for a in ministry]
    sources += [source_entry(m) for m in matches]
    chosen = decide(ministry, feed_values if matches else [])
    vote = majority(sources)
    if vote:
        chosen = vote[0]
    values = sorted({s['amount'] for s in sources if usable(s['amount'])})
    raw_values = {s['amount'] for s in sources if s['amount'] is not None}
    if record.get('procedureGroup', {}).get('kind') == 'lots':
        status = 'notice-checked'
    elif not matches:
        status = 'single-source'
    elif len(raw_values) == 1:
        status = 'sources-agree'
    else:
        status = 'sources-disagree'
    verification = {'status': status, 'sources': sorted({s['source'] for s in sources})}
    if any(placeholder(s['amount']) for s in sources):
        verification['placeholder'] = True
    if len(values) > 1:
        verification['amountRange'] = [values[0], values[-1]]
        if vote:
            verification['majority'] = {'amount': vote[0], 'routes': vote[1], 'of': vote[2]}
    record['amountSources'] = sources
    record['verification'] = verification
    # Offers: two positive counts that differ are two declarations by the same buyer; neither is chosen.
    feed_offers = sorted({m['offresRecues'] for m in rows if isinstance(m.get('offresRecues'), int) and m['offresRecues'] > 0})
    ours = record.get('offers')
    if isinstance(ours, int) and ours > 0 and feed_offers and ours not in feed_offers and not record.get('offersConflict'):
        record['offers'] = None
        record['offersConflict'] = {'decp': ours, 'feed': feed_offers, 'source': rows[0]['sourceDataset']}
        verification['offersDisagree'] = True
    if 'amount' in (record.get('initialConflicts') or []):
        if chosen is not None and chosen in ministry:
            # A pair of Ministry amounts resolved by the buyer's own feed.
            record['initialConflicts'] = [f for f in record['initialConflicts'] if f != 'amount']
            record['amount'] = chosen
            if record.get('history'):
                record['history'][0]['amount'] = chosen
            verification['resolvedPair'] = True
        return
    if record.get('amount') != chosen:
        record['amount'] = chosen
        if record.get('history'):
            record['history'][0]['amount'] = chosen


def add_co_holders(record, rows, stats):
    for row in rows:
        holder = str(row['titulaire_id'])
        if holder in holders(record):
            continue
        entry = {'id': holder, 'identifierType': row.get('titulaire_typeIdentifiant'), 'source': row['sourceDataset']}
        if entry['identifierType'] == 'SIRET' and re.fullmatch(r'\d{14}', holder):
            entry['siren'] = holder[:9]
        record['supplierIds'] = [*(record.get('supplierIds') or []), entry]
        record['supplier'] = ' / '.join(f"{x.get('identifierType') or 'Identifiant'} {x['id']}" for x in record['supplierIds'])
        record['verification']['holdersAddedFromFeed'] = True
        stats['holders.addedFromFeed'] += 1


def finish_added(record, rows):
    """Sources, status and amount of a record that exists only outside the Ministry dataset."""
    sources = [source_entry(m) for m in rows]
    values = sorted({s['amount'] for s in sources if usable(s['amount'])})
    routes = {family(s['source']) for s in sources}
    raw = {s['amount'] for s in sources}
    status = 'sources-disagree' if len(raw) > 1 else 'sources-agree' if len(routes) > 1 else 'single-source'
    record['amountSources'] = sources
    record['verification'] = {'status': status, 'sources': sorted({s['source'] for s in sources}), 'addedFromFeed': True}
    if any(placeholder(s['amount']) for s in sources):
        record['verification']['placeholder'] = True
    vote = majority(sources)
    if len(values) > 1:
        record['verification']['amountRange'] = [values[0], values[-1]]
        if vote:
            record['verification']['majority'] = {'amount': vote[0], 'routes': vote[1], 'of': vote[2]}
    record['amount'] = vote[0] if vote else decide([], [s['amount'] for s in sources])
    if record.get('history'):
        record['history'][0]['amount'] = record['amount']


def resolve_duplicate_clusters(records, by_record, stats):
    """Settle "possibly the same contract" clusters (same holder, object, date, framework) with route evidence.

    - Every member carries its own, different reference in another route: separate contracts.
    - Exactly one member is published by another route and the others by none: one contract whose
      Ministry rows give several amounts (as for the Paris pairs); the others are folded into it.
    Anything else stays flagged."""
    by_id = {r['id']: r for r in records}
    removed, done = set(), set()
    for record in records:
        if not record.get('possibleDuplicateOf') or record['id'] in done:
            continue
        cluster = [record['id'], *record['possibleDuplicateOf']]
        done.update(cluster)
        members = [by_id[i] for i in cluster if i in by_id]
        refs = {m['id']: {(s['source'], s.get('id')) for s in m.get('amountSources', []) if s['source'] != 'ministry'} for m in members}
        confirmed = [m for m in members if refs[m['id']]]
        own_refs = [next(iter(refs[m['id']]))[1] for m in members if len(refs[m['id']]) == 1]
        if len(confirmed) == len(members) and len(own_refs) == len(members) and len(set(own_refs)) == len(members):
            for m in members:
                m.pop('possibleDuplicateOf', None)
                m['verification']['duplicateCleared'] = 'distinct references in another publication route'
            stats['duplicates.cleared'] += len(members)
        elif len(confirmed) == 1 and all(len(m.get('history') or []) <= 1 for m in members if m is not confirmed[0]):
            keep = confirmed[0]
            alternatives = []
            for m in members:
                alternatives += m.get('initialAlternatives') or [{'amount': a} for a in ministry_amounts(m)]
                if m is not keep:
                    keep['sourceRowVariants'] = (keep.get('sourceRowVariants') or []) + (m.get('sourceRowVariants') or [])
                    removed.add(m['id'])
            keep.pop('possibleDuplicateOf', None)
            keep['initialConflicts'] = sorted({*(keep.get('initialConflicts') or []), 'amount'})
            keep['initialAlternatives'] = alternatives
            reconcile_record(keep, by_record.get(keep['id'], []))
            keep['verification']['foldedRows'] = len(members) - 1
            stats['duplicates.folded'] += len(members) - 1
    records[:] = [r for r in records if r['id'] not in removed]


def apply(records, feed, buyers, build, cohort):
    """Reconcile `records` in place and return (added records, statistics).

    Buyer feeds are matched first; the buyers' open-data lists (portal_*) second, against the
    Ministry records and the contracts added from the feeds, so a portal row confirms a feed-only
    contract instead of duplicating it. `build(contract, ids_in_use)` makes a cohort record."""
    stats = defaultdict(int)
    by_record, co_holders = defaultdict(list), defaultdict(list)
    contracts = feed_contracts(feed, buyers)
    phases = [[c for c in contracts if not c['initial']['sourceDataset'].startswith('portal_')],
              [c for c in contracts if c['initial']['sourceDataset'].startswith('portal_')]]
    added, own = [], {}
    in_use = {r['id'] for r in records}
    for phase, batch in enumerate(phases):
        index = Index(records + added)
        unmatched = []
        for contract in batch:
            record, how = index.match(contract['initial'])
            stats[('feed.' if phase == 0 else 'portal.') + how] += 1
            if record:
                by_record[record['id']].append(contract['initial'])
                if how == 'co-holder':
                    co_holders[record['id']].append(contract['initial'])
            elif how == 'absent':
                unmatched.append(contract)
        # One added record per distinct contract: a buyer feed copy wins over the scraped one.
        chosen = {}
        for contract in sorted(unmatched, key=lambda c: (c['initial']['sourceDataset'] == SCRAPED, c['initial']['sourceDataset'], c['initial']['uid'] or '')):
            row = contract['initial']
            key = (row['acheteur_id'], row['titulaire_id'], money(row['montant']), row['dateNotification'], words(row['objet']))
            if key in chosen:
                stats['feed.duplicateAcrossSources'] += 1
                chosen[key]['copies'].append(row)
            else:
                chosen[key] = {**contract, 'copies': []}
        for contract in chosen.values():
            record = build(contract, in_use)
            in_use.add(record['id'])
            own[record['id']] = [contract['initial'], *contract['copies']]
            record['amount'] = money(contract['initial']['montant'])
            added.append(record)
            stats[('records.addedFromFeed' if phase == 0 else 'records.addedFromPortal')] += 1
    for record in records:
        reconcile_record(record, by_record.get(record['id'], []))
        add_co_holders(record, co_holders.get(record['id'], []), stats)
    resolve_duplicate_clusters(records, by_record, stats)
    for record in added:
        finish_added(record, own[record['id']] + by_record.get(record['id'], []))
        add_co_holders(record, co_holders.get(record['id'], []), stats)
    link_shared_identifiers(records + added)
    stats['records.added'] = len(added)
    for record in records + added:
        stats['status.' + record['verification']['status']] += 1
        stats['placeholder'] += bool(record['verification'].get('placeholder'))
        stats['resolvedPair'] += bool(record['verification'].get('resolvedPair'))
        stats['majority'] += bool(record['verification'].get('majority'))
    return added, dict(sorted(stats.items()))


def link_shared_identifiers(records):
    """Every set of records sharing buyer + published identifier is linked; existing groups are extended."""
    groups = defaultdict(list)
    for r in records:
        groups[(r['buyerSiret'], r['contractId'])].append(r)
    for (buyer, cid), members in groups.items():
        if len(members) < 2:
            # A group reduced to one record (rows folded into it) is no longer a shared identifier.
            for r in members:
                if (r.get('procedureGroup') or {}).get('kind') == 'shared-identifier':
                    r.pop('procedureGroup')
            continue
        ids = [r['id'] for r in members]
        kind = 'lots' if all((m.get('procedureGroup') or {}).get('kind') == 'lots' for m in members) else 'shared-identifier'
        for r in members:
            own = r.get('procedureGroup') or {}
            if own and set(own['members']) == set(ids) and (own.get('kind') == kind):
                continue
            group = {k: v for k, v in own.items() if k in ('contractReference', 'lotTitle', 'basis')}
            group.setdefault('basis', 'Le même identifiant DECP est publié pour plusieurs marchés distincts ; chacun est conservé séparément, aucun identifiant n’est inventé.')
            group.update({'id': f'decp-{buyer}-{cid}', 'contractId': cid, 'members': ids, 'kind': kind})
            r['procedureGroup'] = group


def cpv_lookup(records):
    """8-digit CPV -> published full code with check digit, from codes already in the cohort."""
    seen = defaultdict(set)
    for r in records:
        for a in [r, *(r.get('initialAlternatives') or [])]:
            code = a.get('cpv')
            if code and re.fullmatch(r'\d{8}-\d', code):
                seen[code[:8]].add(code)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def feed_fields(contract, cpv_full, direct):
    """Cohort-independent fields of a record added from a feed contract."""
    r = contract['initial']
    number = lambda v: float(v) if isinstance(v, (int, float)) and v >= 0 else None
    holder = r['titulaire_id']
    supplier_ids = [{'id': str(holder), 'identifierType': r.get('titulaire_typeIdentifiant')}] if holder else []
    for s in supplier_ids:
        if s['identifierType'] == 'SIRET' and re.fullmatch(r'\d{14}', s['id']):
            s['siren'] = s['id'][:9]
    cpv = r.get('codeCPV')
    history = [{'kind': 'initial', 'id': r['id'], 'date': r['dateNotification'], 'publicationDate': r.get('datePublicationDonnees'),
                'amount': money(r['montant']), 'durationMonths': number(r.get('dureeMois')), 'supplierId': supplier_ids[0]['id'] if len(supplier_ids) == 1 else None}]
    for m in contract['mods']:
        history.append({'kind': 'modification', 'id': str(m['modification_id']), 'date': m['dateNotification'],
                        'publicationDate': m.get('datePublicationDonnees'), 'amount': money(m['montant']),
                        'durationMonths': number(m.get('dureeMois')), 'supplierId': None})
    return {'amount': money(r['montant']), 'offers': r['offresRecues'] if isinstance(r.get('offresRecues'), int) and r['offresRecues'] >= 0 else None,
            'date': r['dateNotification'], 'durationMonths': number(r.get('dureeMois')),
            'cpv': cpv_full.get(cpv, cpv), 'procedure': r.get('procedure'),
            'priceType': ', '.join(sorted(x.strip() for x in r['typesPrix'].split(','))) if isinstance(r.get('typesPrix'), str) and ',' in r['typesPrix'] else r.get('typesPrix'), 'priceForm': r.get('formePrix'),
            'nature': r.get('nature'), 'description': r.get('objet') or 'Objet non renseigné', 'contractId': r['id'],
            'lotId': None, 'noticeId': None, 'publicationDate': r.get('datePublicationDonnees'), 'frameworkId': r.get('idAccordCadre'),
            'executionModalities': r.get('modalitesExecution'), 'techniques': r.get('techniques'),
            'supplier': ' / '.join(f"{s.get('identifierType') or 'Identifiant'} {s['id']}" for s in supplier_ids) or None,
            'supplierIds': supplier_ids, 'directAward': direct(r.get('procedure')), 'officialFinding': None,
            'dataStatus': 'verified', 'dataFamily': 'decp', 'history': history, 'initialConflicts': [],
            'initialAlternatives': [], 'modificationConflicts': [],
            'feedUid': r['uid'], 'feedSource': r['sourceDataset']}


def new_id(buyer, cid, ids_in_use):
    base = f'decp-{buyer}-{cid}'
    if base not in ids_in_use:
        return base
    n = 2
    while f'{base}-flux-{n}' in ids_in_use:
        n += 1
    return f'{base}-flux-{n}'


def source_text(feed):
    return {'source': feed['source']['dataset_page'],
            'sourceLabel': 'Flux de publication de l’acheteur, via la consolidation nationale DECP (decp.info)'}
