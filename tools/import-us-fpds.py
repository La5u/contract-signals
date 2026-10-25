#!/usr/bin/env python3
"""Research only: slim SQLite copies of the USAspending contract archives (FPDS transactions).

Reads ~/.cache/contract-signals/us-fpds/raw/FY<year>_All_Contracts_Full_<date>.zip (us-fpds/fetch.sh) without
unpacking them and writes one file per fiscal year, us-fpds/db/fy<year>.sqlite:

- `tx`: one row per transaction (contract_transaction_unique_key), the columns in KEEP. Coded fields keep the code
  only; empty strings stay null, amounts are never filled in or summed.
- `codes`: (field, code, description) pairs seen for the coded fields, so the descriptions are stored once.

Left out on purpose: officers' names and pay, phone/fax numbers, street addresses, funding account lists, the
business-type flag block and the COVID/IIJA supplemental amounts. A year is written to <file>.new and renamed
only when complete, so an interrupted run leaves no partial year behind; finished years are skipped on rerun.
"""
import argparse
import csv
import io
import os
import sqlite3
import sys
import time
import zipfile
from multiprocessing import Pool
from pathlib import Path

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/us-fpds'
NUMERIC = ['federal_action_obligation', 'base_and_exercised_options_value', 'base_and_all_options_value',
           'current_total_value_of_award', 'potential_total_value_of_award', 'number_of_offers_received',
           'number_of_actions', 'action_date_fiscal_year']
TEXT = ['contract_transaction_unique_key', 'contract_award_unique_key', 'award_id_piid', 'modification_number',
        'transaction_number', 'parent_award_agency_id', 'parent_award_id_piid', 'action_date',
        'period_of_performance_start_date', 'period_of_performance_current_end_date',
        'period_of_performance_potential_end_date', 'ordering_period_end_date', 'solicitation_date',
        'awarding_agency_code', 'awarding_sub_agency_code', 'awarding_office_code', 'funding_agency_code',
        'funding_sub_agency_code', 'funding_office_code', 'recipient_uei', 'recipient_duns', 'recipient_name',
        'recipient_parent_uei', 'recipient_parent_duns', 'recipient_parent_name', 'cage_code',
        'recipient_country_code', 'recipient_state_code', 'primary_place_of_performance_country_code',
        'primary_place_of_performance_state_code', 'solicitation_identifier', 'transaction_description',
        'last_modified_date']
# (code column, description column); the description goes to `codes`.
CODED = [('awarding_agency_code', 'awarding_agency_name'), ('awarding_sub_agency_code', 'awarding_sub_agency_name'),
         ('awarding_office_code', 'awarding_office_name'), ('funding_agency_code', 'funding_agency_name'),
         ('award_type_code', 'award_type'), ('idv_type_code', 'idv_type'),
         ('multiple_or_single_award_idv_code', 'multiple_or_single_award_idv'),
         ('type_of_contract_pricing_code', 'type_of_contract_pricing'), ('action_type_code', 'action_type'),
         ('product_or_service_code', 'product_or_service_code_description'), ('naics_code', 'naics_description'),
         ('extent_competed_code', 'extent_competed'), ('solicitation_procedures_code', 'solicitation_procedures'),
         ('type_of_set_aside_code', 'type_of_set_aside'), ('evaluated_preference_code', 'evaluated_preference'),
         ('fair_opportunity_limited_sources_code', 'fair_opportunity_limited_sources'),
         ('other_than_full_and_open_competition_code', 'other_than_full_and_open_competition'),
         ('commercial_item_acquisition_procedures_code', 'commercial_item_acquisition_procedures'),
         ('simplified_procedures_for_certain_commercial_items_code',
          'simplified_procedures_for_certain_commercial_items'),
         ('fed_biz_opps_code', 'fed_biz_opps'), ('undefinitized_action_code', 'undefinitized_action'),
         ('cost_or_pricing_data_code', 'cost_or_pricing_data'), ('contract_bundling_code', 'contract_bundling'),
         ('parent_award_type_code', 'parent_award_type'),
         ('parent_award_single_or_multiple_code', 'parent_award_single_or_multiple'),
         ('contracting_officers_determination_of_business_size_code',
          'contracting_officers_determination_of_business_size'),
         ('national_interest_action_code', 'national_interest_action'),
         ('interagency_contracting_authority_code', 'interagency_contracting_authority')]
CODE_COLS = [c for c, _ in CODED if c not in TEXT]
KEEP = TEXT + CODE_COLS + NUMERIC
DESCRIPTION_MAX = 300
BATCH = 20000


def number(v):
    try:
        return float(v) if v != '' else None
    except ValueError:
        return None


def convert(row, index):
    out = []
    for name in KEEP:
        v = row[index[name]]
        if name in NUMERIC:
            out.append(number(v))
        elif v == '':
            out.append(None)
        elif name == 'transaction_description':
            out.append(v[:DESCRIPTION_MAX])
        else:
            out.append(v)
    return out


def import_year(zip_path, out_dir, limit=None):
    year = zip_path.name.split('_')[0][2:]
    target = out_dir / f'fy{year}.sqlite'
    if target.exists():
        return f'{target.name}: exists, skipped'
    tmp = target.with_suffix('.sqlite.new')
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.execute('PRAGMA journal_mode=OFF')
    db.execute('PRAGMA synchronous=OFF')
    db.execute(f'CREATE TABLE tx ({", ".join(n + (" REAL" if n in NUMERIC else " TEXT") for n in KEEP)})')
    db.execute('CREATE TABLE codes (field TEXT, code TEXT, description TEXT, PRIMARY KEY (field, code, description))')
    insert = f'INSERT INTO tx VALUES ({", ".join("?" * len(KEEP))})'
    start, rows, codes = time.time(), 0, set()
    with zipfile.ZipFile(zip_path) as z:
        for member in sorted(n for n in z.namelist() if n.endswith('.csv')):
            with z.open(member) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding='utf-8', newline=''))
                header = next(reader)
                index = {n: i for i, n in enumerate(header)}
                missing = [n for n in KEEP + [d for _, d in CODED] if n not in index]
                if missing:
                    raise SystemExit(f'{member}: missing columns {missing}')
                pairs = [(c, index[c], index[d]) for c, d in CODED]
                batch = []
                for row in reader:
                    if len(row) != len(header):
                        raise SystemExit(f'{member}: row {rows + len(batch) + 2} has {len(row)} fields, not {len(header)}')
                    batch.append(convert(row, index))
                    for field, ci, di in pairs:
                        if row[ci] or row[di]:
                            codes.add((field, row[ci], row[di]))
                    if len(batch) >= BATCH:
                        db.executemany(insert, batch)
                        rows += len(batch)
                        batch = []
                        if limit and rows >= limit:
                            break
                db.executemany(insert, batch)
                rows += len(batch)
            if limit and rows >= limit:
                break
    db.executemany('INSERT OR IGNORE INTO codes VALUES (?, ?, ?)', sorted(codes))
    db.execute('CREATE INDEX tx_award ON tx (contract_award_unique_key)')
    db.commit()
    db.close()
    if limit:
        return f'{tmp.name}: {rows:,} rows (limit {limit}, kept as .new) in {time.time() - start:.0f}s'
    tmp.rename(target)
    return f'{target.name}: {rows:,} rows, {len(codes):,} codes in {time.time() - start:.0f}s'


def run(args):
    return import_year(*args)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--raw', type=Path, default=BASE / 'raw')
    ap.add_argument('--out', type=Path, default=BASE / 'db')
    ap.add_argument('--years', help='comma-separated fiscal years (default: every archive)')
    ap.add_argument('--workers', type=int, default=2, help='years imported in parallel')
    ap.add_argument('--limit', type=int, help='stop each year after about this many rows (test runs)')
    a = ap.parse_args()
    csv.field_size_limit(sys.maxsize)
    a.out.mkdir(parents=True, exist_ok=True)
    zips = sorted(a.raw.glob('FY*_All_Contracts_Full_*.zip'))
    if a.years:
        wanted = {f'FY{y.strip()}' for y in a.years.split(',')}
        zips = [z for z in zips if z.name.split('_')[0] in wanted]
    jobs = [(z, a.out, a.limit) for z in zips]
    if a.workers <= 1:
        for job in jobs:
            print(run(job), flush=True)
        return
    with Pool(a.workers) as pool:
        for message in pool.imap_unordered(run, jobs):
            print(message, flush=True)


if __name__ == '__main__':
    main()
