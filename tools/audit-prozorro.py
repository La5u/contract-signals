#!/usr/bin/env python3
"""Read-only, offline integrity audit for the bounded Prozorro cohort.

Use --live to make at most seven short-timeout requests for the preselected records.
No cohort downloads are performed. Output is deterministic except live-check results.
"""
import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from personal_ids import mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
START, END = "2024-09-01", "2026-09-01"
SIGNED = {"active", "terminated"}
IGNORED_BIDS = {"deleted", "draft"}
COMPETITIVE = {"aboveThreshold", "aboveThresholdEU", "aboveThresholdUA", "aboveThresholdUA.defense", "belowThreshold", "competitiveDialogueEU", "competitiveDialogueUA", "competitiveDialogueEU.stage2", "competitiveDialogueUA.stage2", "competitiveOrdering", "esco", "simple.defense", "requestForProposal", "priceQuotation", "closeFrameworkAgreementUA", "closeFrameworkAgreementSelectionUA"}


def load_record(path):
    return json.loads(gzip.decompress(path.read_bytes()))["data"]


def has_window_date(t):
    day = (t.get("dateCreated") or "")[:10]
    return START <= day < END


def offer_count(t, lot_id):
    bids = [b for b in t.get("bids") or [] if b.get("status") not in IGNORED_BIDS]
    if not t.get("bids"):
        return None
    return sum(any(v.get("relatedLot") == lot_id for v in b.get("lotValues") or []) for b in bids) if lot_id else len(bids)


def supplier_ids(suppliers):
    """Published supplier codes; a 10-digit UA-EDR code is a person's RNOKPP and is masked."""
    ids = []
    for s in suppliers or []:
        identifier = s.get("identifier", {})
        code = str(identifier.get("id") or "")
        personal = identifier.get("scheme") == "UA-EDR" and code.isdigit() and len(code) == 10
        ids.append(mask("RNOKPP", code) if personal else identifier.get("id"))
    return ids


def live_check(t, contract, award, offers, timeout=4):
    url = f"https://public-api.prozorro.gov.ua/api/2.5/tenders/{t['id']}"
    checked_at = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": "contract-signals/0.1 audit"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            current = json.load(response).get("data", {})
        live_awards = {a.get("id"): a for a in current.get("awards") or []}
        live_award = live_awards.get(award.get("id"))
        live_contract = next((c for c in current.get("contracts") or []
                              if c.get("contractID") == contract.get("contractID")), None)
        live_suppliers = supplier_ids(live_award.get("suppliers")) if live_award else None
        live_offers = offer_count(current, (live_award or {}).get("lotID")) if live_award else None
        pairs = {
            "tenderID": (t.get("tenderID"), current.get("tenderID")),
            "internalId": (t.get("id"), current.get("id")),
            "dateCreated": (t.get("dateCreated"), current.get("dateCreated")),
            "buyerId": ((t.get("procuringEntity") or {}).get("identifier", {}).get("id"),
                        (current.get("procuringEntity") or {}).get("identifier", {}).get("id")),
            "contractId": (contract.get("contractID"), (live_contract or {}).get("contractID") if live_contract else None),
            "awardId": (award.get("id"), (live_contract or {}).get("awardID") if live_contract else None),
            "supplierIds": (supplier_ids(award.get("suppliers")), live_suppliers),
            "offerCount": (offers, live_offers),
        }
        fields = {name: {"snapshot": expected, "live": actual,
                         "status": "unavailable" if actual is None else ("match" if expected == actual else "mismatch")}
                  for name, (expected, actual) in pairs.items()}
        mismatches = [k for k, v in fields.items() if v["status"] == "mismatch"]
        unavailable = [k for k, v in fields.items() if v["status"] == "unavailable"]
        return {"result": "mismatch" if mismatches else ("unavailable" if unavailable else "match"),
                "httpStatus": 200, "checkedAt": checked_at, "apiUrl": url,
                "portalUrl": f"https://prozorro.gov.ua/tender/{t.get('tenderID')}",
                "fields": fields, "mismatches": mismatches, "unavailableFields": unavailable,
                "liveStatus": current.get("status")}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return {"result": "unavailable", "checkedAt": checked_at, "apiUrl": url,
                "portalUrl": f"https://prozorro.gov.ua/tender/{t.get('tenderID')}",
                "error": type(e).__name__ + (": " + str(e)[:160] if str(e) else "")}


def audit(root=ROOT, do_live=False):
    raw = root / "data/prozorro/raw"
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    coverage = json.loads((root / "data/prozorro-coverage.json").read_text(encoding="utf-8"))
    rows = json.loads((root / "data/prozorro.json").read_text(encoding="utf-8"))
    files = sorted((raw / "records").glob("*.json.gz"))
    listed, listed_owner = [], {}
    buyer_stats = []
    overlaps = Counter()
    for buyer in manifest["buyers"]:
        ids = buyer["tenderIDs"]
        duplicates = len(ids) - len(set(ids))
        buyer_stats.append({"buyerId": buyer["code"], "searchTotal": buyer["searchTotal"],
                            "listedTenderIDs": buyer["listedTenderIDs"], "manifestWindowIDs": len(ids),
                            "duplicateManifestIDs": duplicates,
                            "searchListingCountConsistent": buyer["searchTotal"] == buyer["listedTenderIDs"]})
        for tid in ids:
            overlaps[tid] += 1
            listed.append(tid)
            listed_owner.setdefault(tid, buyer["code"])
    raw_by_tid, corrupt, filename_mismatch = {}, [], []
    for path in files:
        try:
            t = load_record(path)
        except Exception as e:
            corrupt.append({"file": path.name, "error": type(e).__name__})
            continue
        tid = t.get("tenderID")
        if path.name != f"{tid}.json.gz":
            filename_mismatch.append({"file": path.name, "tenderID": tid})
        if tid in raw_by_tid:
            corrupt.append({"file": path.name, "error": "duplicate raw tenderID", "tenderID": tid})
        raw_by_tid[tid] = t
    absent = sorted(set(listed) - set(raw_by_tid))
    unlisted = sorted(set(raw_by_tid) - set(listed))
    repeated_across_buyers = sorted(tid for tid, n in overlaps.items() if n > 1)
    outside_window, wrong_buyer, tenderid_date_mismatch = [], [], []
    kind_counts, exclusions = Counter(), Counter()
    eligible_sample = []
    joins = Counter()
    multi_contract_awards = Counter()
    bids_unknown = bids_known = 0
    for tid in sorted(set(listed) & set(raw_by_tid)):
        t = raw_by_tid[tid]
        if not has_window_date(t):
            outside_window.append(tid)
            continue
        bid = (t.get("procuringEntity") or {}).get("identifier", {}).get("id")
        if bid != listed_owner[tid]:
            wrong_buyer.append({"tenderID": tid, "listedBuyer": listed_owner[tid], "recordBuyer": bid})
            continue
        kind_counts[t.get("procurementMethodType", "<missing>")] += 1
        if tid[3:13] != (t.get("dateCreated") or "")[:10]:
            tenderid_date_mismatch.append(tid)
        awards = {a.get("id"): a for a in t.get("awards") or []}
        contracts = t.get("contracts") or []
        for c in contracts:
            a = awards.get(c.get("awardID"))
            if not a:
                joins["contract_missing_award"] += 1
            else:
                joins["contract_award_linked"] += 1
                multi_contract_awards[a.get("id")] += 1
            if c.get("status") not in SIGNED:
                exclusions["contract status not signed: " + str(c.get("status"))] += 1
            elif not a or a.get("status") != "active":
                exclusions["no linked active award"] += 1
            elif len(a.get("suppliers") or []) != 1:
                exclusions["award supplier count != 1"] += 1
            else:
                joins["retained_contract_award_supplier"] += 1
                lot_id = a.get("lotID")
                offers = offer_count(t, lot_id) if t.get("procurementMethodType") in COMPETITIVE else None
                if t.get("procurementMethodType") in COMPETITIVE:
                    if offers is None: bids_unknown += 1
                    else: bids_known += 1
                eligible_sample.append((tid, t, c, a, offers))
    for aid, n in multi_contract_awards.items():
        if n > 1:
            joins["awards_with_multiple_contracts"] += 1
    expected_rows = {(r.get("tenderID"), r.get("contractId"), r.get("awardId")): r for r in rows}
    actual = {}
    for tid, t, c, a, offers in eligible_sample:
        actual[(tid, c.get("contractID"), a.get("id"))] = (t, c, a, offers)
    missing_rows = sorted(list(set(actual) - set(expected_rows)))
    extra_rows = sorted(list(set(expected_rows) - set(actual)))
    offer_mismatches = []
    for key in set(actual) & set(expected_rows):
        wanted = actual[key][3]
        if expected_rows[key].get("offers") != wanted:
            offer_mismatches.append({"tenderID": key[0], "contractId": key[1], "snapshot": expected_rows[key].get("offers"), "recomputed": wanted})
    duplicate_output_ids = len(rows) - len({r.get("id") for r in rows})
    row_tender_buyer_issues = []
    for r in rows:
        t = raw_by_tid.get(r.get("tenderID"))
        if not t or r.get("buyerId") != (t.get("procuringEntity") or {}).get("identifier", {}).get("id"):
            row_tender_buyer_issues.append(r.get("tenderID"))
    # Fixed deterministic, source-level sample: 4 likely single-offer signals + 3 unflagged.
    # Single-offer status is the one scored procurement signal in the retained rows per national.cjs.
    score_flagged = [x for x in eligible_sample if x[4] == 1 and x[1].get("procurementMethodType") in COMPETITIVE]
    score_clear = [x for x in eligible_sample if x[4] is not None and x[4] != 1 and x[1].get("procurementMethodType") in COMPETITIVE]
    score_clear += [x for x in eligible_sample if x[1].get("procurementMethodType") == "reporting"]
    def ordered(items):
        return sorted(items, key=lambda x: hashlib.sha256(x[0].encode()).hexdigest())
    chosen, chosen_ids = [], set()
    for item in ordered(score_flagged)[:4] + ordered(score_clear) + ordered(score_flagged)[4:]:
        if item[0] not in chosen_ids:
            chosen.append(item)
            chosen_ids.add(item[0])
        if len(chosen) == 7:
            break
    samples = []
    for tid, t, c, a, offers in chosen:
        sample = {"tenderID": tid, "buyerId": (t.get("procuringEntity") or {}).get("identifier", {}).get("id"),
                  "internalId": t.get("id"), "contractId": c.get("contractID"), "awardId": a.get("id"),
                  "procedure": t.get("procurementMethodType"), "lotId": a.get("lotID"), "snapshotOfferCount": offers,
                  "sampleClass": "single-offer signal" if offers == 1 and t.get("procurementMethodType") in COMPETITIVE else "no single-offer signal",
                  "snapshotJoin": True}
        if do_live:
            sample["liveApi"] = live_check(t, c, a, offers)
        samples.append(sample)
    expected_wrong_buyer_count = coverage["counts"]["tendersWithAnotherBuyer"]
    duplicate_actual_joins = len(eligible_sample) - len({(tid, c.get("contractID"), a.get("id")) for tid, _, c, a, _ in eligible_sample})
    duplicate_snapshot_joins = len(rows) - len(expected_rows)
    unmatched_contracts = [tid for tid, t in raw_by_tid.items()
                           if any(not any(a.get("id") == c.get("awardID") for a in t.get("awards") or [])
                                  for c in t.get("contracts") or [])]
    expected_exclusions = {("contract not signed (" + k.split(": ", 1)[1] + ")") if k.startswith("contract status not signed: ") else k: v
                           for k, v in exclusions.items()}
    coverage_counts = coverage["counts"]
    coverage_mismatches = {
        "tendersInWindow": {"audit": sum(kind_counts.values()), "coverage": coverage_counts["tendersInWindow"]},
        "procedureTypes": {"audit": dict(sorted(kind_counts.items())), "coverage": coverage_counts["procedureTypes"]},
        "retainedContracts": {"audit": len(actual), "coverage": coverage_counts["retainedContracts"]},
        "excludedContracts": {"audit": dict(sorted(expected_exclusions.items())), "coverage": coverage_counts["excludedContracts"]},
        "withOffers": {"audit": bids_known, "coverage": coverage_counts["withOffers"]},
        "tendersOutsideWindowByDateCreated": {"audit": len(outside_window), "coverage": coverage_counts["tendersOutsideWindowByDateCreated"]},
    }
    coverage_mismatches = {k: v for k, v in coverage_mismatches.items() if v["audit"] != v["coverage"]}
    failures = []
    if any(b["duplicateManifestIDs"] for b in buyer_stats) or repeated_across_buyers: failures.append("duplicate manifest IDs")
    if any(not b["searchListingCountConsistent"] for b in buyer_stats): failures.append("inconsistent search totals")
    if duplicate_actual_joins or duplicate_snapshot_joins: failures.append("duplicate join keys")
    if unmatched_contracts: failures.append("unmatched contract awards")
    if coverage_mismatches: failures.append("coverage count/procedure/exclusion mismatches")
    if any(s.get("liveApi", {}).get("result") == "mismatch" for s in samples): failures.append("live field mismatches")
    if any([absent, unlisted, corrupt, filename_mismatch, outside_window, tenderid_date_mismatch,
            len(wrong_buyer) != expected_wrong_buyer_count, missing_rows, extra_rows,
            offer_mismatches, row_tender_buyer_issues, duplicate_output_ids]): failures.append("raw/output integrity mismatches")
    return {
        "auditVersion": 1, "mode": "live-sampled" if do_live else "offline-snapshot-only",
        "criteria": {"date": "record dateCreated ISO date in [2024-09-01, 2026-09-01)", "buyer": "record procuringEntity.identifier.id equals manifest buyer code", "retained": "signed active/terminated contract -> active award -> exactly one supplier", "offerCount": "non-deleted/non-draft bids attributed by bid.lotValues[].relatedLot to the linked award lot; absent bids unknown; reporting not offer-scored"},
        "discovery": {"manifestIDs": len(listed), "uniqueManifestIDs": len(set(listed)), "crossBuyerDuplicateTenderIDs": repeated_across_buyers,
                      "duplicateManifestIDCount": sum(b["duplicateManifestIDs"] for b in buyer_stats),
                      "rawFiles": len(files), "uniqueRawTenderIDs": len(raw_by_tid), "missingRawRecords": absent, "unlistedRawRecords": unlisted,
                      "buyers": buyer_stats, "corruptRecords": corrupt, "filenameTenderIdMismatches": filename_mismatch},
        "matching": {"outsideWindowByRecordDate": outside_window, "listedBuyerMismatch": wrong_buyer, "tenderIdDateVsRecordDateMismatches": tenderid_date_mismatch,
                     "inWindowBuyerMatchedTenders": sum(kind_counts.values()), "procedureTypes": dict(sorted(kind_counts.items())), "coverageTendersInWindow": coverage["counts"]["tendersInWindow"], "coverageTendersWithAnotherBuyer": coverage["counts"]["tendersWithAnotherBuyer"]},
        "joinsAndExclusions": {"counts": dict(sorted(joins.items())), "excludedContracts": dict(sorted(exclusions.items())),
                               "coverageExcludedContracts": coverage["counts"]["excludedContracts"], "retainedRawJoins": len(actual), "snapshotRows": len(rows),
                               "missingSnapshotRows": missing_rows, "extraSnapshotRows": extra_rows, "duplicateOutputIds": duplicate_output_ids,
                               "rowBuyerLinkIssues": row_tender_buyer_issues, "duplicateRawJoinKeys": duplicate_actual_joins,
                               "duplicateSnapshotJoinKeys": duplicate_snapshot_joins, "unmatchedContractAwards": unmatched_contracts,
                               "coverageMismatches": coverage_mismatches},
        "offers": {"competitiveRowsWithCount": bids_known, "competitiveRowsUnknown": bids_unknown,
                   "snapshotOfferMismatches": offer_mismatches},
        "samples": samples,
        "summary": {"status": "issues-found" if failures else "consistent-with-importer-exclusions",
                    "failures": failures,
                    "note": "The 16 site-search buyer mismatches are excluded; independently checked coverage, join, and live-field mismatches fail the audit."}
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="check only deterministic 7-record sample via official API (4s request timeout each)")
    parser.add_argument("--write", type=Path, help="also write JSON report to this path")
    args = parser.parse_args()
    result = audit(do_live=args.live)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        args.write.write_text(text, encoding="utf-8")
    print(text, end="")
    if result["summary"]["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
