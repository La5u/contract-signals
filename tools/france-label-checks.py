#!/usr/bin/env python3
"""France calibration: schema and unlabelled input coverage only (rating not implemented)."""
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
          WHERE cpv_division IS NOT NULL AND naf IS NOT NULL AND acheteur_id IS NOT NULL
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
                 THEN (coalesce(at.n, 0) - coalesce(a.n, 0))::DOUBLE / (dt.n - bt.n) END activity_share,
            CASE WHEN b.dateNotification = f.first_date THEN b.supplier_dependence END share_new
          FROM base b LEFT JOIN sirene s ON b.supplier_siren = s.siren
          LEFT JOIN firsts f ON b.acheteur_id = f.acheteur_id AND b.supplier_siren = f.supplier_siren
          LEFT JOIN activity a ON b.cpv_division = a.cpv_division AND b.naf = a.naf AND b.acheteur_id = a.acheteur_id
          LEFT JOIN activity_totals at ON b.cpv_division = at.cpv_division AND b.naf = at.naf
          LEFT JOIN division_totals dt ON b.cpv_division = dt.cpv_division
          LEFT JOIN buyer_totals bt ON b.cpv_division = bt.cpv_division AND b.acheteur_id = bt.acheteur_id
        ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)""", [str(out / 'measures-supplier.parquet')])
    finally:
        con.close()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decp', type=Path, default=CACHE / 'decp-national-2026-10-30/decp.parquet')
    p.add_argument('--sirene', type=Path, default=CACHE / 'france-sirene/stock-unite-legale.parquet')
    p.add_argument('--temp', type=Path, default=Path('/mnt/data/contract-signals/tmp'))
    p.add_argument('--links', type=Path, default=BASE / 'links-2026-11-01/links.jsonl')
    p.add_argument('--finality', type=Path, default=BASE / 'finality-2026-11-01/finality.jsonl')
    p.add_argument('--family', choices=('irregular-award', 'collusion', 'criminal'), default='irregular-award')
    p.add_argument('--out', type=Path, default=BASE / 'rates-2026-11-01')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--measures', action='store_true')
    p.add_argument('--supplier', action='store_true')
    a = p.parse_args()
    if a.supplier:
        supplier(a.decp, a.sirene, a.out, a.temp)
    elif a.measures:
        measures(a.decp, a.out, a.temp)
    elif a.dry_run:
        dry_run(a.decp, a.sirene, a.temp)
    else:
        p.error('select --supplier, --measures or --dry-run; rating is not implemented')


if __name__ == '__main__':
    main()
