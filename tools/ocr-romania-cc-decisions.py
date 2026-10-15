#!/usr/bin/env python3
"""Research only: OCR the scanned Competition Council decisions (no text layer).

Renders each page with pypdfium2 (200 dpi) and runs Tesseract (Romanian). Resumable per page;
writes ~/.cache/contract-signals/romania-cc/text/<file>.txt when a document is complete.
usage: ocr-romania-cc-decisions.py [--workers N]   (reads romania-cc/scans.txt)
"""
import argparse
import subprocess
import tempfile
from multiprocessing import Pool
from pathlib import Path

import pypdfium2 as pdfium

BASE = Path.home() / '.cache/contract-signals/romania-cc'


def ocr_page(job):
    name, i = job
    out = BASE / 'ocr' / name / f'{i:04d}.txt'
    if out.exists():
        return
    pdf = pdfium.PdfDocument(str(BASE / 'pdf' / name))
    image = pdf[i].render(scale=200 / 72).to_pil().convert('L')
    with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
        image.save(tmp.name)
        text = subprocess.run(['tesseract', tmp.name, '-', '-l', 'ron', '--psm', '3'], capture_output=True, text=True).stdout
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--max-pages', type=int, help='only the first N pages of each document (to classify scans)')
    args = p.parse_args()
    names = [n for n in (BASE / 'scans.txt').read_text().split() if n]
    jobs = [(n, i) for n in names for i in range(min(len(pdfium.PdfDocument(str(BASE / 'pdf' / n))), args.max_pages or 10**6))]
    print(f'{len(names)} documents, {len(jobs)} pages', flush=True)
    with Pool(args.workers) as pool:
        for k, _ in enumerate(pool.imap_unordered(ocr_page, jobs, chunksize=4)):
            if k % 100 == 0:
                print(f'{k}/{len(jobs)} pages', flush=True)
    for n in names if not args.max_pages else []:
        pages = sorted((BASE / 'ocr' / n).glob('*.txt'))
        (BASE / 'text' / f'{n}.txt').write_text('\n\f\n'.join(p.read_text() for p in pages))
    print('done', flush=True)


if __name__ == '__main__':
    main()
