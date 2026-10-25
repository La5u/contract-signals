#!/usr/bin/env python3
"""Download every bidder of every KONEPS tender from the PPS Data Hub report UI-ADOFAA-011R
(조달데이터허브 "입찰공고 기업별 투찰 및 계약내역", data.go.kr 15050832, 이용허락범위 제한 없음), by week of notice date.

The report is a MicroStrategy page opened as the hub's guest user in headless Chromium: notice-date range,
낙찰자/전체 = N (all bidders), then CSV export (UTF-16, tab-separated). Each week is saved as UTF-8 gzip
(~20 MB, ~5 min, a 2010 week has ~660,000 rows) once its record count equals the count the report shows;
weeks already saved are skipped, so reruns resume. 51 columns: tender, buyer, method, estimated, base and reserve
price, every bidder's rank, name, business number, bid amount and rate, disqualification, contract number and
amount. No CEO names. Covers 2010 (checked on 2010-03-02), which the open-standard API also does, on another server:
the two split the years.

Private cache ~/.cache/contract-signals/korea/datahub/<YYYY-MM-DD>.csv.gz (Monday of the week).
Needs Playwright and Chromium; runs headless only.
"""
import argparse
import codecs
import csv
import gzip
import io
import os
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

REPORT = 'https://data.g2b.go.kr/link/AISC001_01/?reptNm=UI-ADOFAA-011R'
TITLE = '입찰공고 기업별 투찰 및 계약내역'
CHROMIUM = '/usr/bin/chromium-browser'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea/datahub'


def weeks(start, end):
    """Monday-to-Sunday weeks covering [start, end), newest first."""
    monday = start - timedelta(days=start.weekday())
    out = []
    while monday < end:
        out.append((monday, monday + timedelta(days=6)))
        monday += timedelta(days=7)
    return out[::-1]


MAX_ROWS = 950_000   # the server cancels larger CSV exports


class TooBig(Exception):
    pass


def log(lo, message):
    print(f'{lo}: {message}', file=sys.stderr, flush=True)


def export(lo, hi, raw, max_rows=None):
    """Run the report for notice dates lo..hi and save the CSV export to raw; returns the row count shown."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROMIUM, downloads_path=str(CACHE / 'tmp'),   # not tmpfs
                                    args=['--enable-gpu', '--use-angle=gl-egl', '--ignore-gpu-blocklist'])
        try:
            ctx = browser.new_context(viewport={'width': 1600, 'height': 1000}, locale='ko-KR', accept_downloads=True)
            ctx.set_default_timeout(600000)
            page = ctx.new_page()
            page.goto(REPORT, wait_until='load', timeout=300000)   # networkidle: the site keeps polling, sometimes never idle
            page.get_by_text(TITLE).first.wait_for(timeout=300000)
            page.wait_for_timeout(3000)
            with ctx.expect_page() as opened:
                page.get_by_text(TITLE).first.click()
            report = opened.value
            report.wait_for_load_state('load')
            report.wait_for_timeout(12000)
            dates = [i for i in report.query_selector_all('input') if re.fullmatch(r'\d{4}/\d\d/\d\d', i.input_value() or '')]
            if len(dates) < 2:
                raise RuntimeError('date inputs not found')
            for field, day in zip(dates[:2], (lo, hi)):
                field.click()
                field.press('Control+a')
                field.type(day.strftime('%Y%m%d'))
                field.press('Tab')
            got = [d.input_value() for d in dates[:2]]
            if got != [lo.strftime('%Y/%m/%d'), hi.strftime('%Y/%m/%d')]:
                raise RuntimeError(f'dates not set: {got}')
            report.check('#mf_popupCnts_comp5_input_1', force=True)   # 낙찰자[Y] / 전체[N]: N
            report.get_by_text('검색', exact=True).first.click()
            log(lo, 'searching')
            shown = None
            for _ in range(120):   # up to 20 min for the grid
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
            log(lo, f'{shown} rows shown, exporting')
            if shown == 0:
                return 0
            if max_rows and shown > max_rows:
                raise TooBig(shown, (hi - lo).days + 1)
            for click in range(3):   # the first click often opens nothing: click again after 30 s, then 2 min
                try:
                    with ctx.expect_page(timeout=30000 if click == 0 else 120000) as dialog_opened:
                        report.get_by_text('CSV다운로드').first.click()
                    break
                except Exception:
                    log(lo, f'no export window after click {click + 1}')
                    if click == 2:
                        report.screenshot(path=str(CACHE / 'tmp' / f'{lo}-noexport.png'))
                        raise
            dialog = dialog_opened.value
            dialog.wait_for_load_state()
            dialog.wait_for_timeout(3000)
            with dialog.expect_download(timeout=900000) as download:   # a week takes 2-4 min; some exports hang
                dialog.locator('input[value="내보내기"], button:has-text("내보내기")').first.click()
            log(lo, 'downloading')
            download.value.save_as(raw)
            download.value.delete()   # the browser's own copy in downloads_path, else one file per export piles up
            return shown
        finally:
            browser.close()


def convert(raw, out, header):
    """Appends the UTF-16 export's records (without the prompt preamble) to the csv writer out, the header row too
    when header is True; returns the number of data records."""
    records = 0
    with open(raw, 'rb') as f:
        rows = csv.reader(io.TextIOWrapper(f, encoding='utf-16', newline=''), delimiter='\t')
        started = False
        for row in rows:
            if not started:
                if row and row[0] == '조달방식':
                    started = True
                    if header:
                        out.writerow(row)
                continue
            if any(row):
                out.writerow(row)
                records += 1
    return records


def week(lo, hi, attempts=4):
    """A week in one export, or after a failure in parts (the server cancels exports of over ~1 million rows)."""
    target = CACHE / f'{lo}.csv.gz'
    raw = CACHE / 'tmp' / f'{lo}.csv'
    raw.parent.mkdir(parents=True, exist_ok=True)
    size = (hi - lo).days + 1
    for attempt in range(1, attempts + 1):
        started = time.time()
        days = (hi - lo).days + 1
        parts = [(lo + timedelta(days=d), min(hi, lo + timedelta(days=d + size - 1))) for d in range(0, days, size)]
        part = target.with_suffix('.part')
        try:
            total = 0
            with gzip.open(part, 'wt', encoding='utf-8', newline='') as f:
                out = csv.writer(f, delimiter='\t')
                for a, b in parts:
                    shown = export(a, b, raw, MAX_ROWS if b > a else None)
                    records = convert(raw, out, total == 0) if shown else 0
                    raw.unlink(missing_ok=True)
                    if records != shown:
                        raise RuntimeError(f'{a}..{b}: {records} records exported, {shown} shown')
                    total += records
            part.rename(target)
            print(f'{lo}..{hi}: {total} rows in {len(parts)} export(s), {time.time() - started:.0f} s', flush=True)
            return total
        except Exception as error:
            # next time smaller parts: sized from the row count when the week was too big, else halved
            size = (max(1, min(size - 1, int(error.args[1] * 0.8 * MAX_ROWS / error.args[0]))) if isinstance(error, TooBig)
                    else max(1, size // 2) if 'canceled' in str(error) else size)   # other errors: same parts again
            print(f'{lo}..{hi}: attempt {attempt}/{attempts} ({len(parts)} parts): {type(error).__name__}: {str(error)[:300]}', flush=True)
            if attempt == attempts:
                traceback.print_exc()
        finally:
            raw.unlink(missing_ok=True)
        time.sleep(30)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--start', default='2010-01-01')
    parser.add_argument('--end', default='2017-01-01', help='exclusive')
    parser.add_argument('--workers', type=int, default=3, help='browsers at once (~5 min and ~600 MB of disk per week each)')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [(lo, hi) for lo, hi in weeks(date.fromisoformat(args.start), date.fromisoformat(args.end))
            if not (CACHE / f'{lo}.csv.gz').exists()]
    print(f'{len(todo)} weeks to fetch', flush=True)
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(week, *zip(*todo))) if todo else []
    failed = sum(r is None for r in results)
    print(f'done: {len(results) - failed} weeks saved, {failed} failed', flush=True)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
