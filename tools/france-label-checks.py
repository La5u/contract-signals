#!/usr/bin/env python3
"""France calibration: input coverage, contract measures and label ratings."""
import argparse
from pathlib import Path

import duckdb

CACHE = Path.home() / '.cache/contract-signals'
BASE = CACHE / 'france-admin'

# Availability of inputs, not the number of evaluable contracts. These are raw
# initial-state rows, including duplicate publications and flattened holders.
CHECKS = {
    'BID-COUNT': 'offresRecues IS NOT NULL AND procedure IS NOT NULL',
    'DIRECT': 'procedure IS NOT NULL',
    'NEAR-LIMIT': 'montant > 0 AND dateNotification IS NOT NULL AND type IS NOT NULL',
    'AMEND-COUNT': "d.dateNotification IS NOT NULL AND d.dateNotification <= DATE '2026-11-01' - INTERVAL 24 MONTH",
    'AMEND-PRICE': "d.montant > 0 AND m.last_amount IS NOT NULL",
    'TERM-EXTENSION': "d.dureeMois IS NOT NULL AND m.last_duration IS NOT NULL",
    'DURATION': 'dureeMois IS NOT NULL AND dureeMois >= 0',
    'SIGN-DATE': 'dateNotification IS NOT NULL',
    'BUYER-SHARE': 'montant > 0 AND acheteur_id IS NOT NULL AND dateNotification IS NOT NULL',
    'SUPPLIER-DEPENDENCE': 'montant > 0 AND acheteur_id IS NOT NULL AND dateNotification IS NOT NULL AND titulaire_id IS NOT NULL',
    'CONCENTRATION': 'acheteur_id IS NOT NULL AND codeCPV IS NOT NULL AND titulaire_id IS NOT NULL',
    'REPEATED-SINGLE-BID': 'acheteur_id IS NOT NULL AND codeCPV IS NOT NULL AND offresRecues IS NOT NULL AND procedure IS NOT NULL',
    'REPEATED-DIRECT': 'acheteur_id IS NOT NULL AND codeCPV IS NOT NULL AND titulaire_id IS NOT NULL AND procedure IS NOT NULL',
    'NEW-SUPPLIER': 'acheteur_id IS NOT NULL AND titulaire_id IS NOT NULL AND dateNotification >= DATE \'2022-01-01\'',
    'FRAMEWORK': 'idAccordCadre IS NOT NULL',
    'CONSORTIUM': 'typeGroupementOperateurs IS NOT NULL',
    'SUBCONTRACTING': 'sousTraitanceDeclaree IS NOT NULL',
    'SUPPLIER-TYPE': 'titulaire_typeIdentifiant IS NOT NULL',
    'ROUND-NUMBERS A1/A2': 'FALSE',
    'ROUND-NUMBERS A3/A4': 'montant > 0',
    'ROUND-NUMBERS A5/A6': 'FALSE',
    'ROUND-NUMBERS A7': 'montant > 0 AND titulaire_id IS NOT NULL',
    'LATE-PUBLICATION': 'dateNotification IS NOT NULL AND datePublicationDonnees IS NOT NULL AND datePublicationDonnees >= dateNotification',
    'SUPPLIER-DISTANCE': 'titulaire_distance IS NOT NULL AND titulaire_distance >= 0',
    'SUPPLIER-SIZE': 'titulaire_categorie IS NOT NULL',
    'SUPPLIER-AGE': 'dateNotification IS NOT NULL AND dateCreationUniteLegale IS NOT NULL',
    'SUPPLIER-CLOSED': 'dateNotification IS NOT NULL AND etatAdministratifUniteLegale IN (\'A\', \'C\') AND (etatAdministratifUniteLegale = \'A\' OR dateDebut IS NOT NULL)',
    'ACTIVITY-MISMATCH': 'codeCPV IS NOT NULL AND titulaire_activite_code IS NOT NULL AND acheteur_id IS NOT NULL',
    'SUPPLIER-SHARE-NEW': 'montant > 0 AND acheteur_id IS NOT NULL AND titulaire_id IS NOT NULL AND dateNotification >= DATE \'2022-01-01\'',
}


def dry_run(decp, sirene, temp):
    temp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit = '4GB'")
    con.execute('SET temp_directory = ?', [str(temp)])
    con.from_parquet(str(decp)).create_view('decp')
    con.from_parquet(str(sirene)).create_view('sirene')
    total, uids = con.execute('SELECT count(*), count(DISTINCT uid) FROM decp').fetchone()
    initial = con.execute('SELECT count(*) FROM decp WHERE modification_id = 0').fetchone()[0]
    print(f'DECP rows: {total}; distinct UIDs: {uids}; initial-state rows: {initial}')
    dates = con.execute('''SELECT count(*), count(dateNotification), count(datePublicationDonnees),
                           count(*) FILTER (WHERE dateNotification IS NOT NULL OR datePublicationDonnees IS NOT NULL)
                           FROM decp WHERE modification_id > 0''').fetchone()
    print(f'Modification rows: {dates[0]}; notification dated: {dates[1]}; publication dated: {dates[2]}; either: {dates[3]}')
    print('Modification date proxy: notification, else publication; rows, not distinct modifications.')
    print('Coverage: initial-state rows with required fields; not deduplicated or evaluated contracts.')
    con.execute('''CREATE TEMP TABLE mods AS
        SELECT uid, arg_max(montant, coalesce(dateNotification, datePublicationDonnees)) last_amount,
               arg_max(dureeMois, coalesce(dateNotification, datePublicationDonnees)) last_duration
        FROM decp WHERE modification_id > 0
        GROUP BY uid''')
    expressions = ', '.join(f'count(*) FILTER (WHERE {v})' for v in CHECKS.values())
    sql = f'''SELECT {expressions} FROM decp d LEFT JOIN mods m USING (uid) LEFT JOIN sirene s
              ON upper(d.titulaire_typeIdentifiant) = 'SIRET'
              AND regexp_full_match(d.titulaire_id, '[0-9]{{14}}')
              AND substr(d.titulaire_id, 1, 9) = s.siren
              WHERE d.modification_id = 0'''
    counts = con.execute(sql).fetchone()
    print('Check | Rows with required fields')
    for name, count in zip(CHECKS, counts):
        print(f'{name} | {count}')
    con.close()



def measures(decp, out, temp):
    """Build unlabelled contract measures; no court labels are read here."""
    out.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit = '3GB'")
    con.execute('SET temp_directory = ?', [str(temp)])
    con.from_parquet(str(decp)).create_view('decp')
    # Count distinct modification IDs, not the flattened holder rows. An
    # undated modification makes the 24-month count unknowable.
    sql = r"""
    COPY (
    WITH initial AS (
      SELECT * EXCLUDE (rn, holders) , holders FROM (
        SELECT *, row_number() OVER (PARTITION BY uid ORDER BY titulaire_id NULLS LAST,
          titulaire_typeIdentifiant NULLS LAST, montant NULLS LAST, dateNotification NULLS LAST) rn,
          count(DISTINCT titulaire_id) OVER (PARTITION BY uid) holders
        FROM decp WHERE modification_id = 0 AND uid IS NOT NULL
      ) WHERE rn = 1
    ), modifications AS (
      SELECT uid, modification_id, min(coalesce(dateNotification, datePublicationDonnees)) mod_date,
        max(montant) montant, max(dureeMois) duree
      FROM decp WHERE modification_id > 0 AND uid IS NOT NULL GROUP BY uid, modification_id
    ), mods AS (
      SELECT i.uid,
        CASE WHEN i.dateNotification IS NOT NULL
                  AND i.dateNotification + INTERVAL 24 MONTH <= DATE '2026-10-30'
                  AND count(*) FILTER (WHERE m.modification_id IS NOT NULL AND m.mod_date IS NULL) = 0
             THEN count(*) FILTER (WHERE m.mod_date >= i.dateNotification
                         AND m.mod_date <= i.dateNotification + INTERVAL 24 MONTH) END amend_count_24m,
        arg_max(m.montant, (m.mod_date, m.modification_id)) FILTER (WHERE m.mod_date IS NOT NULL) last_amount,
        arg_max(m.duree, (m.mod_date, m.modification_id)) FILTER (WHERE m.mod_date IS NOT NULL) last_duration,
        count(m.modification_id) n_mods
      FROM initial i LEFT JOIN modifications m USING(uid) GROUP BY i.uid, i.dateNotification
    ), base AS (
      SELECT i.*, year(dateNotification) AS "year",
        CASE WHEN regexp_full_match(acheteur_id, '[0-9]{9}([0-9]{5})?') THEN left(acheteur_id, 9) END siren,
        CASE WHEN regexp_matches(codeCPV, '^[0-9]{2}') THEN left(codeCPV, 2) END cpv_division,
        CASE WHEN upper(titulaire_typeIdentifiant) = 'SIRET' AND regexp_full_match(titulaire_id, '[0-9]{14}')
             THEN left(titulaire_id, 9) END supplier_siren,
        CASE WHEN procedure IS NULL OR trim(procedure) = '' THEN NULL
             WHEN lower(procedure) LIKE '%sans publicité ni mise en concurrence préalable%' THEN true
             ELSE false END direct
      FROM initial i
    ), agg AS (
      SELECT *,
        sum(CASE WHEN montant > 0 THEN montant END) OVER (PARTITION BY acheteur_id, "year") buyer_total,
        sum(CASE WHEN montant > 0 THEN montant END) OVER (PARTITION BY acheteur_id, "year", supplier_siren) supplier_total,
        count(*) OVER (PARTITION BY acheteur_id, cpv_division) division_count,
        count(*) OVER (PARTITION BY acheteur_id, cpv_division, supplier_siren) supplier_count,
        avg(CASE WHEN direct = false AND offresRecues > 0 THEN (offresRecues = 1)::INTEGER END)
          OVER (PARTITION BY acheteur_id, cpv_division) single_rate,
        sum(CASE WHEN direct THEN 1 ELSE 0 END) OVER (PARTITION BY acheteur_id, cpv_division, supplier_siren) direct_count,
        count(*) OVER (PARTITION BY acheteur_id, supplier_siren ORDER BY dateNotification
          RANGE BETWEEN INTERVAL 3 YEAR PRECEDING AND INTERVAL 1 DAY PRECEDING) prior_count
      FROM base
    )
    SELECT a.uid, acheteur_id, siren, "year", montant, type, cpv_division, titulaire_id, holders, procedure,
      CASE WHEN direct = false AND offresRecues > 0 THEN offresRecues END bid_count, direct,
      amend_count_24m,
      CASE WHEN montant > 0 AND last_amount IS NOT NULL THEN 100.0 * last_amount / montant END amend_price_pct,
      CASE WHEN dureeMois >= 0 AND last_duration IS NOT NULL THEN last_duration > dureeMois END term_extension,
      CASE WHEN dureeMois >= 0 THEN dureeMois END duree_mois,
      CASE WHEN dateNotification IS NOT NULL THEN month(dateNotification) = 12 END sign_december,
      CASE WHEN dateNotification IS NOT NULL THEN dayofweek(dateNotification) IN (0, 6) END sign_weekend,
      CASE WHEN acheteur_id IS NOT NULL AND "year" IS NOT NULL AND montant > 0 THEN montant / buyer_total END buyer_share,
      CASE WHEN acheteur_id IS NOT NULL AND "year" IS NOT NULL AND supplier_siren IS NOT NULL AND montant > 0
           THEN supplier_total / buyer_total END supplier_dependence,
      CASE WHEN acheteur_id IS NOT NULL AND cpv_division IS NOT NULL AND supplier_siren IS NOT NULL
                AND division_count >= 10 THEN supplier_count::DOUBLE / division_count END concentration,
      CASE WHEN acheteur_id IS NOT NULL AND cpv_division IS NOT NULL THEN single_rate END repeated_single_bid,
      CASE WHEN acheteur_id IS NOT NULL AND cpv_division IS NOT NULL AND supplier_siren IS NOT NULL AND direct IS NOT NULL
           THEN direct_count END repeated_direct,
      CASE WHEN acheteur_id IS NOT NULL AND supplier_siren IS NOT NULL AND dateNotification >= DATE '2022-01-01'
           THEN prior_count = 0 END new_supplier,
      CASE WHEN idAccordCadre IS NOT NULL AND trim(idAccordCadre) <> '' THEN true END framework,
      CASE WHEN typeGroupementOperateurs IN ('Solidaire', 'Conjoint') THEN true
           WHEN typeGroupementOperateurs = 'Pas de groupement' THEN false END consortium,
      sousTraitanceDeclaree subcontracting,
      CASE WHEN titulaire_typeIdentifiant IS NOT NULL AND trim(titulaire_typeIdentifiant) <> ''
           THEN upper(titulaire_typeIdentifiant) <> 'SIRET' END supplier_type_other,
      CASE WHEN montant > 0 AND dateNotification IS NOT NULL THEN montant /
           CASE WHEN dateNotification >= DATE '2020-01-01' THEN 40000.0 ELSE 25000.0 END END near_limit_ratio,
      CASE WHEN montant > 0 THEN montant / pow(10, floor(log10(montant)) - 1) = round(montant / pow(10, floor(log10(montant)) - 1)) END round_amount,
      CASE WHEN datePublicationDonnees >= dateNotification THEN date_diff('day', dateNotification, datePublicationDonnees) END late_publication_days,
      CASE WHEN titulaire_distance >= 0 THEN titulaire_distance END supplier_distance,
      titulaire_categorie supplier_category
    FROM agg a LEFT JOIN mods m USING(uid)
    ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)
    """
    try:
        con.execute(sql, [str(out / 'measures.parquet')])
    finally:
        con.close()

def supplier(decp, sirene, out, temp):
    """Add supplier measures, using the current closed period as closure date."""
    out.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit = '3GB'")
    con.execute('SET temp_directory = ?', [str(temp)])
    try:
        con.from_parquet(str(out / 'measures.parquet')).create_view('measures')
        con.from_parquet(str(decp)).create_view('decp')
        con.from_parquet(str(sirene)).create_view('sirene')
        con.execute(r"""CREATE TEMP TABLE base AS
          WITH initial AS (
            SELECT uid, dateNotification, titulaire_activite_code, titulaire_typeIdentifiant,
              row_number() OVER (PARTITION BY uid ORDER BY titulaire_id NULLS LAST,
                titulaire_typeIdentifiant NULLS LAST, montant NULLS LAST, dateNotification NULLS LAST) rn
            FROM decp WHERE modification_id = 0 AND uid IS NOT NULL
          )
          SELECT m.*, i.dateNotification,
            CASE WHEN upper(i.titulaire_typeIdentifiant) = 'SIRET'
                      AND regexp_full_match(m.titulaire_id, '[0-9]{14}')
                 THEN left(m.titulaire_id, 9) END supplier_siren,
            CASE WHEN regexp_matches(i.titulaire_activite_code, '^[0-9]{2}')
                 THEN left(i.titulaire_activite_code, 2) END naf
          FROM measures m LEFT JOIN initial i ON m.uid = i.uid AND i.rn = 1""")
        con.execute("""CREATE TEMP TABLE activity AS
          SELECT cpv_division, naf, acheteur_id, count(*) n FROM base
          WHERE cpv_division IS NOT NULL AND acheteur_id IS NOT NULL
          GROUP BY ALL""")
        con.execute("""CREATE TEMP TABLE activity_totals AS
          SELECT cpv_division, naf, sum(n) n FROM activity GROUP BY ALL""")
        con.execute("""CREATE TEMP TABLE division_totals AS
          SELECT cpv_division, sum(n) n FROM activity GROUP BY ALL""")
        con.execute("""CREATE TEMP TABLE buyer_totals AS
          SELECT cpv_division, acheteur_id, sum(n) n FROM activity GROUP BY ALL""")
        con.execute("""COPY (
          WITH firsts AS (
            SELECT acheteur_id, supplier_siren, min(dateNotification) first_date
            FROM base WHERE acheteur_id IS NOT NULL AND supplier_siren IS NOT NULL
            GROUP BY ALL
          )
          SELECT b.uid,
            CASE WHEN s.dateCreationUniteLegale <= b.dateNotification
                 THEN date_diff('month', s.dateCreationUniteLegale, b.dateNotification) END supplier_age_months,
            CASE WHEN b.dateNotification <= DATE '2026-11-01' AND
                 ((s.etatAdministratifUniteLegale = 'A') OR
                  (s.etatAdministratifUniteLegale = 'C' AND s.dateDebut BETWEEN b.dateNotification AND DATE '2026-11-01'))
                 THEN date_diff('month', b.dateNotification,
                    CASE WHEN s.etatAdministratifUniteLegale = 'C' THEN s.dateDebut ELSE DATE '2026-11-01' END) END months_to_closure,
            CASE WHEN b.dateNotification <= DATE '2026-11-01' AND
                 ((s.etatAdministratifUniteLegale = 'A') OR
                  (s.etatAdministratifUniteLegale = 'C' AND s.dateDebut BETWEEN b.dateNotification AND DATE '2026-11-01'))
                 THEN s.etatAdministratifUniteLegale = 'A' END closure_censored,
            CASE WHEN b.dateNotification <= DATE '2026-11-01' AND s.etatAdministratifUniteLegale IN ('A', 'C')
                 THEN date_diff('month', b.dateNotification, DATE '2026-11-01') END observable_months,
            CASE WHEN b.naf IS NOT NULL AND b.acheteur_id IS NOT NULL AND dt.n - bt.n > 0
                 THEN (coalesce(act_total.n, 0) - coalesce(a.n, 0))::DOUBLE / (dt.n - bt.n) END activity_share,
            CASE WHEN b.dateNotification = f.first_date THEN b.supplier_dependence END share_new
          FROM base b LEFT JOIN sirene s ON b.supplier_siren = s.siren
          LEFT JOIN firsts f ON b.acheteur_id = f.acheteur_id AND b.supplier_siren = f.supplier_siren
          LEFT JOIN activity a ON b.cpv_division = a.cpv_division AND b.naf = a.naf AND b.acheteur_id = a.acheteur_id
          LEFT JOIN activity_totals act_total ON b.cpv_division = act_total.cpv_division AND b.naf = act_total.naf
          LEFT JOIN division_totals dt ON b.cpv_division = dt.cpv_division
          LEFT JOIN buyer_totals bt ON b.cpv_division = bt.cpv_division AND b.acheteur_id = bt.acheteur_id
        ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)""", [str(out / 'measures-supplier.parquet')])
    finally:
        con.close()

# The statistical routines and range selection are shared with the Korean calibration.
def rate(measures_dir, links_path, finality_path, family, out):
    import importlib.util
    import json
    import math
    import numpy as np

    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    curves = load('france_curves', 'korea-curves.py')
    pp, bc = curves.pp, curves.bc
    # Euro value bands; thresholds are reported with the results.
    edges = [40000, 100000, 250000, 1000000, 5000000, 20000000]
    def read_jsonl(path):
        with path.open(encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]
    links, fins = read_jsonl(links_path), read_jsonl(finality_path)
    fin = {x['ruling']: x for x in fins}
    linked = [x for x in links if x.get('uid') and x.get('class') in ('A1', 'A2', 'A3', 'C')]
    missing = sorted({x['ruling'] for x in linked} - fin.keys())
    if missing:
        raise ValueError(f'finality missing for {len(missing)} linked rulings')
    actions = {}
    for path in sorted(links_path.parent.parent.glob('extract*/checked.jsonl')):
        for x in read_jsonl(path):
            if x.get('id'):
                actions[x['id']] = ((x.get('result') or {}).get('case') or {}).get('action')
    con = duckdb.connect()
    try:
        con.from_parquet(str(measures_dir / 'measures.parquet')).create_view('m')
        con.from_parquet(str(measures_dir / 'measures-supplier.parquet')).create_view('s')
        ids = list({x['uid'] for x in linked})
        con.execute('CREATE TEMP TABLE linked(uid VARCHAR)')
        if ids:
            con.executemany('INSERT INTO linked VALUES (?)', [(x,) for x in ids])
        cur = con.execute('''SELECT m.*, s.* EXCLUDE(uid) FROM m LEFT JOIN s USING(uid)
            WHERE (m.acheteur_id, m.year) IN
              (SELECT m.acheteur_id, m.year FROM m JOIN linked USING(uid)
               WHERE m.acheteur_id IS NOT NULL AND m.year IS NOT NULL)''')
        cols = [x[0] for x in cur.description]
        contracts = [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()
    by_uid = {}
    for x in linked:
        by_uid.setdefault(x['uid'], []).append(x)
    # Class meanings are specific to the administrative linker.
    if family != 'irregular-award':
        raise ValueError('this links format only defines the irregular-award family (A1/A2/A3/C)')
    numeric = {'AMEND-PRICE':'amend_price_pct', 'DURATION':'duree_mois', 'BUYER-SHARE':'buyer_share',
        'SUPPLIER-DEPENDENCE':'supplier_dependence', 'CONCENTRATION':'concentration',
        'REPEATED-SINGLE-BID':'repeated_single_bid', 'LATE-PUBLICATION':'late_publication_days',
        'SUPPLIER-DISTANCE':'supplier_distance', 'SUPPLIER-AGE':'supplier_age_months',
        'ACTIVITY-MISMATCH':'activity_share', 'SUPPLIER-SHARE-NEW':'share_new', 'NEAR-LIMIT':'near_limit_ratio'}
    binary = {'DIRECT':'direct', 'TERM-EXTENSION':'term_extension', 'SIGN-DATE december':'sign_december',
        'SIGN-DATE weekend':'sign_weekend', 'NEW-SUPPLIER':'new_supplier', 'FRAMEWORK':'framework',
        'CONSORTIUM':'consortium', 'SUBCONTRACTING':'subcontracting', 'SUPPLIER-TYPE':'supplier_type_other',
        'ROUND-NUMBERS A3/A4':'round_amount'}
    def round_increase(pct):
        # A1 on final vs signed amount: a whole-percent rise of at least 1 %, not a ratio p/q with q <= 9.
        if pct is None or not math.isfinite(pct):
            return None
        step = pct - 100
        if step < 1 - 1e-6 or abs(step - round(step)) > 1e-6:
            return False
        ratio = round(pct) / 100
        return not any(abs(ratio * q - round(ratio * q)) < 1e-9 for q in range(1, 10))
    def closed_24m(c):
        # Ceased within 24 months; only contracts notified at least 24 months before the SIRENE extract.
        if c.get('closure_censored') is None or c.get('observable_months') is None or c['observable_months'] < 24:
            return None
        return not c['closure_censored'] and c['months_to_closure'] <= 24
    derived = {'ROUND-NUMBERS A1': lambda c: round_increase(c.get('amend_price_pct')),
               'SUPPLIER-CLOSED': closed_24m}
    # Count indicators are discrete bins, evaluated against every other known count.
    counts = {'BID-COUNT': ('bid_count', [(1,2),(2,3),(3,4),(4,6),(6,11),(11,None)]),
              'AMEND-COUNT': ('amend_count_24m', [(0,1),(1,2),(2,3),(3,5),(5,None)]),
              'REPEATED-DIRECT': ('repeated_direct', [(0,1),(1,2),(2,3),(3,5),(5,None)])}
    sections = {}
    variants = ['main', 'comparison C', 'DIRECT outside A2', 'BID-COUNT non-ousted actions',
                'pending w=0', 'pending w=1', 'A1+A2 alone']
    for variant in variants:
        rows = []
        for c in contracts:
            candidates = by_uid.get(c['uid'], [])
            positive = [x for x in candidates if x['class'] in ('A1','A2','A3')]
            if variant == 'DIRECT outside A2':
                positive = [x for x in positive if x['class'] != 'A2']
            elif variant == 'BID-COUNT non-ousted actions':
                positive = [x for x in positive if actions.get(x['ruling']) in ('prefect_referral', 'validity_third_party')]
            elif variant == 'A1+A2 alone':
                positive = [x for x in positive if x['class'] in ('A1','A2')]
            if variant == 'comparison C':
                pool = [x for x in candidates if x['class'] == 'C']
            else:
                pool = []
            def weight(x):
                f = fin[x['ruling']]
                w = 0 if f['status'] == 'overturned' else f['w']
                if f['status'] == 'pending' and variant in ('pending w=0', 'pending w=1'):
                    w = int(variant[-1])
                return float(x['class_probability'] or 0) * float(x['probability'] or 0) * float(w)
            group = 'combined' if positive else 'comparison' if pool or not candidates else None
            selected = positive if positive else pool
            if variant == 'comparison C' and not selected:
                continue
            if not group:
                continue
            best = max(selected, key=weight) if selected else None
            w = weight(best) if best else 1.0
            if w <= 0:
                continue
            ch = {name: c.get(col) for name, col in numeric.items()}
            ch['_amount'] = c.get('montant')
            for name, col in binary.items():
                v = c.get(col)
                ch[name] = None if v is None else bool(v)
            for name, f in derived.items():
                ch[name] = f(c)
            for name, (col, bins) in counts.items():
                v = c.get(col)
                for lo, hi in bins:
                    ch[f'{name} {lo}-{hi if hi is not None else "+"}'] = None if v is None else lo <= v and (hi is None or v < hi)
            category = c.get('supplier_category')
            for cat in ('PME', 'ETI', 'GE', 'MICRO'):
                ch[f'SUPPLIER-CATEGORY {cat}'] = None if category is None else category == cat
            rows.append({'id':c['uid'], 'buyer':c['acheteur_id'], 'case':best['ruling'] if best else None,
                         'groups':[group], 'weight':w, 'checks':ch})
        names = list(numeric) + list(binary) + list(derived) + [f'{n} {lo}-{hi if hi is not None else "+"}' for n, (_, bins) in counts.items() for lo, hi in bins] + [f'SUPPLIER-CATEGORY {x}' for x in ('PME','ETI','GE','MICRO')]
        if variant == 'DIRECT outside A2': names = ['DIRECT']
        if variant == 'BID-COUNT non-ousted actions': names = [n for n in names if n.startswith('BID-COUNT ')]
        results = []
        for name in names:
            known = [r for r in rows if r['checks'].get(name) is not None]
            pos = [r for r in known if 'combined' in r['groups']]
            buyers = sum(max(r['weight'] for r in pos if r['buyer'] == b) for b in {r['buyer'] for r in pos})
            if buyers < pp.MIN_BUYERS or not any('comparison' in r['groups'] for r in known):
                results.append({'check':name, 'skip':f'fewer than {pp.MIN_BUYERS} weighted labelled buyers or no evaluable comparisons', 'labelled_buyers':buyers})
                continue
            lo = hi = None
            if name in numeric:
                d = curves.Data(rows, name)
                # Use the same value-band control and case-held-out range selection as Korea.
                d.band = np.array([bc.band(a / 1.3 if lab else a, edges) for a, lab in zip(d.amount, d.lab)])
                size = name in ('BUYER-SHARE','SUPPLIER-DEPENDENCE')
                if size:
                    d.reweight(d.band, len(edges) + 1)
                pct = np.unique(np.quantile(d.comp_x, np.arange(1,100)/100))
                cell, ncell = d.cells(pct), len(pct)+1
                matrix, folds = curves.cv_range(d, cell, ncell)
                if sum(f is not None for f in folds) < 2 or not np.isfinite(matrix).any():
                    results.append({'check':name, 'skip':'fewer than two scorable folds or no eligible range', 'labelled_buyers':buyers})
                    continue
                i, j = np.unravel_index(np.argmin(matrix), matrix.shape)
                gains = []
                for k, fold in enumerate(folds):
                    if fold is not None:
                        a, b = curves.best_range(d, cell, ncell, mask=d.fold != k)
                        if np.isfinite(fold[a, b]):
                            gains.append(float(np.log(2) - fold[a, b]))
                accepted = len(gains) >= 2 and np.mean(gains) > np.std(gains, ddof=1) / np.sqrt(len(gains))
                lo = -math.inf if i == 0 else float(pct[i-1])
                hi = math.inf if j == ncell else float(pct[j-1])
                test = lambda v: lo <= v < hi
            else:
                test = bool
            rated = [dict(r, checks={name: {'status': 'unknown' if r['checks'].get(name) is None else 'signal' if test(r['checks'][name]) else 'clear'}}) for r in rows]
            res = pp.analyse(rated, name)
            if name in numeric:
                res['range'] = [None if math.isinf(lo) else lo, None if math.isinf(hi) else hi]
                res['range_accepted'] = bool(accepted)
                if not accepted:
                    res['decision_points'] = 0.0
            if name in ('BUYER-SHARE','SUPPLIER-DEPENDENCE') or name.startswith('SUPPLIER-CATEGORY '):
                units = [(r['buyer'], 'combined' in r['groups'], r['weight'], r['checks'][name]['status'],
                          {'value':bc.band(float(original['checks']['_amount']) / (1.3 if 'combined' in r['groups'] else 1), edges)})
                         for r, original in zip(rated, rows) if original['checks']['_amount'] is not None and original['checks']['_amount'] > 0]
                res['value_control'] = bc.analyse(units, name, ['value'], pp.SEED) if units else None
                control = res['value_control']
                res['decision_points'] = (control['points'] if control and buyers >= pp.MIN_BUYERS
                                          and (name not in numeric or accepted) else 0.0)
            results.append(res)
        sections[variant] = results
    # Explicitly identify unavailable measures rather than silently omitting them.
    sections['unavailable'] = [{'check':x, 'skip':'required measure is not present in the measures files'} for x in
        ('ROUND-NUMBERS A2', 'ROUND-NUMBERS A5/A6 (DECP has no budget field)', 'ROUND-NUMBERS A7')]
    out.mkdir(parents=True, exist_ok=True)
    data = {'family':family, 'value_band_edges_eur':edges, 'sections':sections}
    (out / f'rate-{family}.json').write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    lines = [f'France: {family}', 'Value bands (EUR): ' + ', '.join(map(str, edges)), '']
    for section, results in sections.items():
        lines += [f'## {section}', '| Check | Labelled buyers | Label hit rate | Comparison hit rate | LR | Shrunk LR | Points |', '|---|---:|---:|---:|---:|---:|---:|']
        for r in results:
            if 'skip' in r:
                lines.append(f"| {r['check']} | {r.get('labelled_buyers', '')} | {r['skip']} | | | | |")
            else:
                lines.append(f"| {r['check']} {r.get('range', '')} | {r['combined']['buyers']} | {r['combined']['rate']} | {r['comparison']['rate']} | {r['lr_raw']} | {r['lr_shrunk']} | {r['decision_points']} |")
                if 'value_control' in r:
                    lines.append(f"| value control | | | | | | {r['value_control']} |")
        lines.append('')
    (out / f'rate-{family}.txt').write_text('\n'.join(lines), encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decp', type=Path, default=CACHE / 'decp-national-2026-10-30/decp.parquet')
    p.add_argument('--sirene', type=Path, default=CACHE / 'france-sirene/stock-unite-legale.parquet')
    p.add_argument('--temp', type=Path, default=Path('/mnt/data/contract-signals/tmp'))
    p.add_argument('--links', type=Path, default=BASE / 'links-2026-11-01/links.jsonl')
    p.add_argument('--finality', type=Path, default=BASE / 'finality-2026-11-01/finality.jsonl')
    p.add_argument('--family', choices=('irregular-award', 'collusion', 'criminal'), default='irregular-award')
    p.add_argument('--out', type=Path, default=BASE / 'rates-2026-11-01')
    p.add_argument('--measures-dir', type=Path, default=BASE / 'measures-2026-11-01')
    p.add_argument('--rate', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--measures', action='store_true')
    p.add_argument('--supplier', action='store_true')
    a = p.parse_args()
    if a.rate:
        rate(a.measures_dir, a.links, a.finality, a.family, a.out)
    elif a.supplier:
        supplier(a.decp, a.sirene, a.out, a.temp)
    elif a.measures:
        measures(a.decp, a.out, a.temp)
    elif a.dry_run:
        dry_run(a.decp, a.sirene, a.temp)
    else:
        p.error('select --rate, --supplier, --measures or --dry-run')


if __name__ == '__main__':
    main()
