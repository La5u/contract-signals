#!/usr/bin/env python3
"""Research only: filter Judilibre procurement offences and read the selected criminal rulings."""
import importlib.util
import json
import os
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cartel', HERE / 'extract-france-cartel-rulings.py')
cartel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cartel)
BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/france-judilibre'

PROMPT = """ruling.txt in this directory is one French Judilibre ruling found by a broad procurement-offence search.
Many are unrelated. Read ALL of it (use your file tools; it can be long, so read it in parts and do not
stop early) and write result.json in this directory (nothing else), one JSON object:

relevant: true if the court addresses favouritism (432-14 code pénal) or receiving its proceeds, corruption
  (432-11, 433-1), influence peddling, unlawful taking of interest (432-12), misappropriation (432-15), or bid
  rigging (L. 420-6 code de commerce), tied to a specific public contract or tender. Include acquittals and quashed
  convictions as well as convictions, so that they can be excluded. Mere background allegations are not findings.
relevant_reason: short explanation.
case: {case_no, court, decision_date, level, earlier_rulings (list of {court, case_no, date}), later_rulings
  (same structure), same_facts_hints (identifiers or facts useful to match trial, appeal and cassation),
  appeal_hints (what is pending, dismissed, quashed or remanded, and what remains decided)}.
findings: list per offence and defendant role: {offence (as printed), article (as printed or null), defendant_role
  ("official" / "elected_member" / "supplier" / "intermediary" / "other" / "unknown"), defendant (as printed,
  including pseudonym, or null), outcome ("convicted" / "acquitted" / "quashed" / "undecided"), outcome_note
  (explain lower-court conviction upheld, quashed or remanded; distinguish what THIS ruling decides), quote
  (verbatim excerpt of ruling.txt, at most 250 characters, stating the finding), contracts: list EVERY contract
  or tender tied to this finding: {buyer, object, lot, amount (euros as a number), amount_vat ("HT" / "TTC" /
  null), notice_date, award_date, signature_date (YYYY-MM-DD or YYYY-MM if stated), winner, winner_siren (only if
  printed), quote (verbatim excerpt of ruling.txt, at most 250 characters identifying the contract)}}.
confidence: "high" if clear and you read all of it, else "low"; unsure: short note or null.

Rules: copy names, numbers and quotes exactly as in ruling.txt (quotes must be found verbatim in the file; copy them
from the file, do not retype). Never guess a buyer, date or amount that is not printed. If relevant is false,
findings may be []. When done, answer only: DONE <number of contracts>.
"""

# Normalize accents and apostrophes before matching; the broad terms deliberately favor recall over precision.
PROC = re.compile(r"\b(?:marches? publics?|marches? de (?:travaux|fournitures|services)|appel[s]? d.offres?|"
                  r"commande publique|contrats? publics?|contrats? de (?:la commande publique|concession)|"
                  r"delegations? de service public|mise en concurrence|attribution (?:d.un |du |de |des |"
                  r"d.une )?(?:marche|contrat|lot|concession)|adjudication|soumissionnaires?|"
                  r"attribution|pouvoir adjudicateur|code (?:des marches publics|de la commande publique))\b")
OFFENCE = re.compile(r"\b(?:favoritisme|favoris(?:er|me|ation)|recel|corruption|corromp(?:u|ue|us|ues|re|ant)|"
                     r"pots?[- ]de[- ]vin|trafic d.influence|prise illegale d.interets?|"
                     r"detournement (?:de fonds|de biens|de deniers|de fonds publics)|"
                     r"soustraction (?:de fonds|de biens|de deniers)|concussion|"
                     r"entente|pratiques? anticoncurrentielles?|collusion|concertation frauduleuse|"
                     r"fausser (?:le jeu de )?la concurrence|432\s*[-–]\s*(?:11|12|14|15)|"
                     r"433\s*[-–]\s*1\b|420\s*[-–]\s*6\b|"
                     r"liberte d.acces et (?:a )?l.egalite (?:des|de traitement des) candidats)\b")


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def ruling_text(rid):
    d = json.loads((BASE / 'decisions' / f'{rid}.json').read_text())
    meta = {k: d.get(k) for k in ('id', 'jurisdiction', 'chamber', 'decision_date', 'number', 'ecli', 'solution', 'partial')}
    head = '\n'.join(f'{k}: {v}' for k, v in meta.items() if v is not None)
    return meta, head + '\n\n' + (d.get('text') or '') + '\n'


def filter_decisions(out):
    kept, dropped, missing = [], 0, []
    for path in sorted((BASE / 'decisions').glob('*.json')):
        d = json.loads(path.read_text())
        text = d.get('text')
        if not isinstance(text, str) or not text.strip():
            missing.append(path.stem)
        s = normalize(text or '')
        if PROC.search(s) and OFFENCE.search(s):
            kept.append(path.stem)
        else:
            dropped += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / 'to-read.txt').write_text('\n'.join(kept) + ('\n' if kept else ''))
    print(f'{len(kept)} kept, {dropped} dropped, {len(kept) + dropped} total; {len(missing)} missing or empty texts')


def main():
    p = cartel.parser(None, 'opencode-go/deepseek-v4.1-flash', 6)
    p.add_argument('--filter', action='store_true', help='write to-read.txt; --out defaults to france-judilibre')
    args = p.parse_args()
    if not 1 <= args.workers <= 6 or (args.limit is not None and args.limit < 0):
        p.error('workers must be between 1 and 6 and limit nonnegative')
    if args.filter:
        if args.check or args.only is not None:
            p.error('--filter cannot be combined with --check or --only')
        return filter_decisions(args.out or BASE)
    args.out = args.out or BASE / 'extract-deepseek'
    args.out.mkdir(parents=True, exist_ok=True)
    if args.check:
        return cartel.check(args.out, 'criminal')
    ids = (BASE / 'to-read.txt').read_text().split()
    cartel.read(ids, args, PROMPT, ruling_text, 'criminal')


if __name__ == '__main__':
    main()
