#!/usr/bin/env python3
"""Download every contract and shopping-mall delivery request (납품요구) for chosen goods classes from the PPS Data Hub
report UI-ADOXFA-190R (조달데이터허브 "특정품목 조달 내역", data.go.kr 15050835, 이용허락범위 제한 없음), by calendar year.

Why: KFTC decisions on 다수공급자계약 (MAS) second-stage competitions (e.g. 14663 GRP pipe, 15581 PE-coated steel
pipe, 14711 hume pipe) name tenders whose award is a delivery request under a framework contract, not a contract of
its own, so they are missing from the open-standard contracts and bid results. This report lists them: one row per
item line of each contract or delivery request (number, change order, date, name, demanding body, supplier name and
business number, MAS flag, 이단계경쟁제안서제출여부 = awarded through a second-stage competition, unit price,
quantity, amount). Supplier names are today's names (한국화이바 shows as 스페이스프로); match on business number.

The report is opened as the hub's guest user in headless Chromium, as in fetch-korea-datahub-bids.py: date range
(at most 12 months), goods class chosen in the 물품분류 popup (8 digits), search, CSV export. A year is saved as UTF-8
gzip once its record count equals the count the report shows; saved years are skipped, so reruns resume.
Private cache ~/.cache/contract-signals/korea/datahub-items/<class>/<year>.csv.gz. Needs Playwright and Chromium.
"""
import argparse
import csv
import gzip
import importlib.util
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

_spec = importlib.util.spec_from_file_location('hub', Path(__file__).resolve().parent / 'fetch-korea-datahub-bids.py')
hub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hub)
REPORT = 'https://data.g2b.go.kr/link/AISC001_01/?reptNm=UI-ADOXFA-190R'
TITLE = '특정품목 조달 내역'
CACHE = hub.CACHE.parent / 'datahub-items'
# goods classes of the KFTC MAS second-stage decisions (detailed codes from decision 14663 and the bid data)
CLASSES = {'40142194': 'GRP pipe (14663)', '40142389': 'GRP fittings (14663)', '30121699': 'plastic manholes (14663)',
           '40142189': 'PE-coated steel pipe (15581)', '40142109': 'centrifugal RC (hume) pipe (14711)'}


def log(tag, message):
    print(f'{tag}: {message}', file=sys.stderr, flush=True)


def export(cls, year, raw):
    """Run the report for goods class cls and contract/delivery dates in year; save the CSV to raw; return rows shown."""
    from playwright.sync_api import sync_playwright
    tag = f'{cls}/{year}'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=hub.CHROMIUM, downloads_path=str(CACHE / 'tmp'),
                                    args=['--enable-gpu', '--use-angle=gl-egl', '--ignore-gpu-blocklist'])
        try:
            ctx = browser.new_context(viewport={'width': 1600, 'height': 1000}, locale='ko-KR', accept_downloads=True)
            ctx.set_default_timeout(600000)
            page = ctx.new_page()
            page.goto(REPORT, wait_until='load', timeout=300000)
            page.get_by_text(TITLE, exact=True).first.wait_for(timeout=400000)   # inexact also hits a hidden menu button
            page.wait_for_timeout(3000)
            with ctx.expect_page() as opened:
                page.get_by_text(TITLE, exact=True).first.click()
            report = opened.value
            report.wait_for_load_state('load')
            report.wait_for_timeout(12000)
            dates = [i for i in report.query_selector_all('input') if re.fullmatch(r'\d{4}/\d\d/\d\d', i.input_value() or '')]
            if len(dates) < 2:
                raise RuntimeError('date inputs not found')
            for field, day in zip(dates[:2], (f'{year}0101', f'{year}1231')):
                field.click()
                field.press('Control+a')
                field.type(day)
                field.press('Tab')
            got = [d.input_value() for d in dates[:2]]
            if got != [f'{year}/01/01', f'{year}/12/31']:
                raise RuntimeError(f'dates not set: {got}')
            report.locator('#mf_popupCnts_comp5_1').click()   # 물품분류 popup; the field itself is read-only
            report.wait_for_timeout(6000)
            query = report.locator('#comPopup_wframe_popupCnts_srchDataParam1')
            query.click()
            query.type(cls)
            report.locator('#comPopup_wframe_popupCnts_btnS0001').click()
            report.wait_for_timeout(6000)
            report.locator('#G_comPopup_wframe_popupCnts_grdList___checkbox_CHK_0').check(force=True)
            report.locator('#comPopup_wframe_popupCnts_btnClose').click()
            report.wait_for_timeout(3000)
            chosen = report.locator('#mf_popupCnts_comp5_3').input_value()
            if not chosen.endswith(':' + cls):
                raise RuntimeError(f'class not set: {chosen!r}')
            report.get_by_text('검색', exact=True).first.click()
            log(tag, 'searching')
            shown = None
            for _ in range(120):
                report.wait_for_timeout(10000)
                for frame in report.frames:
                    try:
                        text = frame.inner_text('body')
                    except Exception:
                        continue
                    m = re.search(r'데이터 행:\s*[\d,]+\s*-\s*[\d,]+\s*/\s*([\d,]+)', text)
                    if m:
                        shown = int(m.group(1).replace(',', ''))
                    elif '데이터가 없' in text or '결과가 없' in text:
                        shown = 0
                if shown is not None:
                    break
            if shown is None:
                raise RuntimeError('no result grid')
            log(tag, f'{shown} rows shown, exporting')
            if shown == 0:
                return 0
            for click in range(3):   # the first click often opens nothing
                try:
                    with ctx.expect_page(timeout=30000 if click == 0 else 120000) as dialog_opened:
                        report.get_by_text('CSV다운로드').first.click()
                    break
                except Exception:
                    log(tag, f'no export window after click {click + 1}')
                    if click == 2:
                        raise
            dialog = dialog_opened.value
            dialog.wait_for_load_state()
            dialog.wait_for_timeout(3000)
            with dialog.expect_download(timeout=900000) as download:
                dialog.locator('input[value="내보내기"], button:has-text("내보내기")').first.click()
            download.value.save_as(raw)
            download.value.delete()
            return shown
        finally:
            browser.close()


def year_file(cls, year, attempts=4):
    target = CACHE / cls / f'{year}.csv.gz'
    raw = CACHE / 'tmp' / f'{cls}-{year}.csv'
    target.parent.mkdir(parents=True, exist_ok=True)
    raw.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, attempts + 1):
        started = time.time()
        part = target.with_suffix('.part')
        try:
            with gzip.open(part, 'wt', encoding='utf-8', newline='') as f:
                shown = export(cls, year, raw)
                records = hub.convert(raw, csv.writer(f, delimiter='\t'), True) if shown else 0
            if records != shown:
                raise RuntimeError(f'{records} records exported, {shown} shown')
            part.rename(target)
            print(f'{cls}/{year}: {records} rows, {time.time() - started:.0f} s', flush=True)
            return records
        except Exception as error:
            print(f'{cls}/{year}: attempt {attempt}/{attempts}: {type(error).__name__}: {str(error)[:300]}', flush=True)
            if attempt == attempts:
                traceback.print_exc()
        finally:
            raw.unlink(missing_ok=True)
        time.sleep(30)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--classes', default=','.join(CLASSES), help='8-digit goods classes, comma-separated')
    parser.add_argument('--start', type=int, default=2010)
    parser.add_argument('--end', type=int, default=2016, help='inclusive')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    todo = [(c, y) for c in args.classes.split(',') for y in range(args.start, args.end + 1)
            if not (CACHE / c / f'{y}.csv.gz').exists()]
    print(f'{len(todo)} class-years to fetch', flush=True)
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(year_file, *zip(*todo))) if todo else []
    failed = sum(r is None for r in results)
    print(f'done: {len(results) - failed} saved, {failed} failed', flush=True)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
