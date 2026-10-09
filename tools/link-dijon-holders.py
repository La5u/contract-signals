#!/usr/bin/env python3
"""Exact-SIRET register check linking Dijon DECP holders to award-notice winners.

The award notice's winner registration numbers are placeholders, so each DECP
holder SIRET is looked up once in the official company register
(recherche-entreprises.api.gouv.fr, DINUM) and compared with the winner name and
postcode printed for the candidate lot. Default is offline linkage over an
existing frozen fetch; --fetch performs the bounded exact-SIRET requests.
Identifiers are read from private evidence and written only to private output.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-conflict-dijon'
REGISTRY = 'https://recherche-entreprises.api.gouv.fr/search'
MAX_BYTES = 512 * 1024
# Legal-form and filler tokens that never establish identity on their own.
NOISE = {'SARL', 'SAS', 'SASU', 'SA', 'EURL', 'SNC', 'ETS', 'ETABLISSEMENTS', 'ENTREPRISE', 'STE', 'SOCIETE', 'ET', 'DE', 'DES', 'DU', 'LA', 'LE', 'LES'}

spec = importlib.util.spec_from_file_location('dijon_reconcile', ROOT / 'tools/reconcile-dijon-conflict.py')
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)


def tokens(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().upper()
    return {t for t in re.split(r'[^A-Z0-9]+', value) if t and t not in NOISE}


def names_agree(winner, names):
    """Distinctive tokens of one name contained in the other (either direction); legal forms ignored."""
    w = tokens(winner)
    return bool(w) and any((w <= tokens(n) or tokens(n) <= w) and tokens(n) for n in names)


def holder_sirets(ministry):
    """Exactly one SIRET per row, or the row cannot be linked."""
    result = []
    for row in ministry:
        ids = rec.identifiers(row)
        result.append(next(iter(ids)) if len(ids) == 1 else None)
    return result


def winners(record):
    """Technical lot -> list of winner {name, postcode} from the exact notice chain."""
    notice = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
    ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
    nr = ext['efac:NoticeResult']
    orgs = rec.unique(ext['efac:Organizations']['efac:Organization'], lambda x: x['efac:Company']['cac:PartyIdentification']['cbc:ID'])
    tenders = rec.unique(nr['efac:LotTender'], lambda x: x['cbc:ID'])
    parties = rec.unique(nr['efac:TenderingParty'], lambda x: x['cbc:ID'])
    result = {}
    for lr in rec.many(nr['efac:LotResult']):
        if not lr.get('efac:LotTender') or isinstance(lr['efac:LotTender'], list):
            continue
        tender = tenders[rec.text(lr['efac:LotTender']['cbc:ID'])]
        party = parties[rec.text(tender['efac:TenderingParty']['cbc:ID'])]
        found = []
        for ref in rec.many(party['efac:Tenderer']):
            company = orgs[rec.text(ref['cbc:ID'])]['efac:Company']
            found.append({'name': rec.text(company.get('cac:PartyName', {}).get('cbc:Name')),
                          'postcode': rec.text(company.get('cac:PostalAddress', {}).get('cbc:PostalZone'))})
        result[rec.text(lr['efac:TenderLot']['cbc:ID'])] = found
    return result


def register_entry(response, siret):
    """The exact establishment from a register response, or None if absent/ambiguous."""
    matches = []
    for company in response.get('results', []):
        for est in company.get('matching_etablissements', []):
            if est.get('siret') == siret:
                matches.append((company, est))
    if len(matches) != 1:
        return None
    company, est = matches[0]
    names = [company.get('nom_complet'), company.get('nom_raison_sociale'), company.get('sigle')]
    names += list(est.get('liste_enseignes') or []) + [est.get('nom_commercial')]
    return {'names': [n for n in names if n], 'postcode': est.get('code_postal'),
            'establishmentState': est.get('etat_administratif'), 'siren': company.get('siren'),
            'sirenMatchesSiret': company.get('siren') == siret[:9]}


def link(candidates, sirets, lot_winners, responses):
    """Per candidate: holder linked only on exact SIRET + name-token + postcode agreement."""
    out = []
    for c in candidates:
        siret = sirets[c['ministryRowIndex']]
        entry = {'ministryRowIndex': c['ministryRowIndex'], 'technicalLotId': c.get('technicalLotId'),
                 'printedLotNumber': c.get('printedLotNumber'), 'holderLinked': False}
        win = lot_winners.get(c.get('technicalLotId'), [])
        reg = register_entry(responses.get(siret) or {}, siret) if siret else None
        if c.get('candidateCount') != 1 or len(win) != 1 or reg is None:
            entry['reason'] = 'no unique candidate lot, winner or exact register establishment'
            out.append(entry)
            continue
        w = win[0]
        name_ok = names_agree(w['name'], reg['names'])
        post_ok = bool(w['postcode']) and w['postcode'] == reg['postcode']
        entry.update(registerSirenConsistent=reg['sirenMatchesSiret'], nameAgrees=name_ok,
                     postcodeAgrees=post_ok, establishmentState=reg['establishmentState'],
                     holderLinked=reg['sirenMatchesSiret'] and name_ok and post_ok)
        out.append(entry)
    # Each register-linked winner may account for only one DECP row.
    linked = [e['technicalLotId'] for e in out if e['holderLinked']]
    if len(linked) != len(set(linked)):
        for e in out:
            e['holderLinked'] = False
            e['reason'] = 'non-unique holder-to-lot linkage'
    return out


def fetch(root, sirets, cap=6):
    if root == ROOT or ROOT in root.parents:
        raise ValueError('Raw responses must stay outside the served repository')
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    root.chmod(0o700)
    plan = {'register': REGISTRY, 'sirets': sorted(set(s for s in sirets if s)),
            'policy': {'maxRequests': cap, 'maxBytes': MAX_BYTES, 'timeoutSeconds': 15,
                       'spacingSeconds': 2, 'redirects': False, 'retries': 0}}
    if len(plan['sirets']) > plan['policy']['maxRequests']:
        raise ValueError('More holder SIRETs than the frozen request cap')
    with (root / 'registry-plan.json').open('x') as stream:  # exclusive freeze; no repeat requests
        stream.write(json.dumps(plan, indent=2) + '\n')
    (root / 'registry-plan.json').chmod(0o600)
    opener = urllib.request.build_opener(rec_no_redirect())
    entries = []
    for siret in plan['sirets']:
        if entries:
            time.sleep(2)
        url = REGISTRY + '?q=' + siret + '&page=1&per_page=5'
        entry = {'siret': siret, 'url': url, 'retrievedAt': datetime.now(timezone.utc).isoformat()}
        body = b''
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'ContractSignals bounded accuracy review', 'Accept-Encoding': 'identity'})
            try:
                response = opener.open(request, timeout=15)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                entry['status'] = response.code
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    entry['truncated'] = True
                    body = body[:MAX_BYTES]
        except Exception as exc:
            entry['error'] = type(exc).__name__
        path = root / (siret + '.response')
        with path.open('xb') as stream:
            stream.write(body)
        path.chmod(0o600)
        entry.update(file=path.name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        entries.append(entry)
        if entry.get('error') or entry.get('truncated') or entry.get('status') in (403, 429) or entry.get('status', 0) >= 500:
            break
    manifest = root / 'registry-manifest.json'
    with manifest.open('x') as stream:
        stream.write(json.dumps({'entries': entries, 'planned': len(plan['sirets'])}, indent=2) + '\n')
    manifest.chmod(0o600)
    print(json.dumps([{'status': e.get('status'), 'bytes': e['bytes'], 'error': e.get('error')} for e in entries]))


def rec_no_redirect():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    return NoRedirect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=CACHE)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    root = args.evidence_dir.resolve()
    if root == ROOT or ROOT in root.parents:
        parser.error('Private evidence must remain outside repository')
    discovery = root / 'official-discovery-20261008'
    ministry = json.loads((discovery / 'ministry-exact.response').read_text())['results']
    boamp = json.loads((discovery / 'boamp-contract-reference.response').read_text())['results']
    record = [r for r in boamp if r['idweb'] == rec.NOTICE]
    if len(record) != 1:
        raise ValueError('Missing or ambiguous exact award notice')
    sirets = holder_sirets(ministry)
    registry_dir = root / 'holder-registry-20261008'
    if args.fetch:
        fetch(registry_dir, sirets)
    manifest = json.loads((registry_dir / 'registry-manifest.json').read_text())
    responses = {}
    for e in manifest['entries']:
        body = (registry_dir / e['file']).read_bytes()
        if e.get('status') != 200 or e.get('truncated') or hashlib.sha256(body).hexdigest() != e['sha256']:
            continue
        responses[e['siret']] = json.loads(body)
    findings = rec.reconcile(ministry, record[0])
    linkage = link(findings['candidates'], sirets, winners(record[0]), responses)
    result = {'register': REGISTRY, 'registryResponses': len(responses), 'linkage': linkage,
              'basis': 'Exact DECP holder SIRET in official register; register name and establishment postcode agree with the notice winner of the candidate lot',
              'limits': ['Register state is current, not as at notification', 'No signed contract or notification letter reviewed',
                         'Offer-count disagreements are not resolved by holder linkage']}
    out = root / 'holder-linkage.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    out.chmod(0o600)
    print(json.dumps({'candidates': len(linkage), 'holdersLinked': sum(e['holderLinked'] for e in linkage),
                      'publishedChanges': 0}))


if __name__ == '__main__':
    main()
