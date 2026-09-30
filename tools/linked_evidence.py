"""Conservative checks over exact, already-published record links; no networking."""
from datetime import datetime, timedelta, timezone


def bid_attrition(tender, winning_award, competitive):
    """All other submitted lot bids explicitly rejected as unqualified.

    'Unsuccessful' alone is NOT proof of disqualification. Pending/cancelled or
    conflicting award decisions make the check unknown; no inferred finality.
    """
    result = {"status": "unknown", "submitted": None, "rejected": None,
              "reason": "Complete, unambiguous bid decisions for this lot are not available.", "decisions": []}
    if not competitive:
        return {**result, "status": "not-applicable", "reason": "Not a competitive procedure."}
    if tender.get("status") != "complete":
        return result
    lot = winning_award.get("lotID")
    bids = [b for b in tender.get("bids") or [] if b.get("status") not in ("deleted", "draft")
            and (any(v.get("relatedLot") == lot for v in b.get("lotValues") or []) if lot else not tender.get("lots"))]
    ids = [b.get("id") for b in bids]
    if not ids or any(not i for i in ids) or len(set(ids)) != len(ids):
        return result
    result["submitted"] = len(ids)
    if len(ids) < 2:
        return {**result, "status": "not-applicable", "reason": "Fewer than two submitted bids; single-offer check is separate."}
    winner = winning_award.get("bid_id")
    if winner not in ids or winning_award.get("status") != "active":
        return result
    outcomes = {}
    for award in tender.get("awards") or []:
        if award.get("lotID") != lot:
            continue
        bid = award.get("bid_id")
        if bid not in ids or bid in outcomes:
            return result
        outcomes[bid] = award
    if set(outcomes) != set(ids):
        return result
    rejected, decisions = 0, []  # attached only to a conclusive result
    for bid in ids:
        award = outcomes[bid]
        if bid == winner:
            if award.get("id") != winning_award.get("id") or award.get("qualified") is not True or award.get("eligible") is not True:
                return result
        elif award.get("status") == "unsuccessful" and award.get("qualified") is False:
            rejected += 1
        else:
            return result  # a loser may be unexamined, not an admissible second bid
        decisions.append({"awardId": award.get("id"), "bidId": bid,
                                    "status": award.get("status"), "qualified": award.get("qualified"),
                                    "title": award.get("title"), "description": award.get("description")})
    return {**result, "status": "signal", "rejected": rejected, "decisions": decisions,
            "reason": f"{rejected} of {len(ids)} published lot bids explicitly rejected as unqualified; one qualified, eligible winner. Reasons may be lawful."}


def notice_change(current, previous):
    """Check ONE explicit predecessor/lot pair, never claim a complete history.

    Five-point candidate: lot title or award criteria changed, correction published
    within seven days before the prior deadline, and no deadline extension. Entire
    publication day (UTC +/-14h envelope) must satisfy the window; date-only
    publication never gets an invented timestamp.
    """
    result = {"status": "unknown", "reason": "Exact predecessor, same procedure/lot and consistent deadlines required."}
    c, p = current.get("noticeEvidence", {}), previous.get("noticeEvidence", {}) if previous else {}
    if c.get("kind") != "correction":
        return {**result, "status": "not-applicable", "reason": "Not a correction notice."}
    if not previous or not c.get("procedureId") or c.get("procedureId") != p.get("procedureId") or not c.get("lotId") or c.get("lotId") != p.get("lotId"):
        return result
    if c.get("deadlineConflict") or p.get("deadlineConflict"):
        return result
    try:
        old = datetime.fromisoformat(p["deadline"]["iso"].replace("Z", "+00:00"))
        new = datetime.fromisoformat(c["deadline"]["iso"].replace("Z", "+00:00"))
        published = datetime.strptime(c["publicationDate"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if old.tzinfo is None or new.tzinfo is None or p["publicationDate"] >= c["publicationDate"]:
            return result
    except (KeyError, TypeError, ValueError):
        return result
    result.update({"previousNoticeId": p.get("noticeId"), "previousSource": p.get("source"),
                   "oldDeadline": p["deadline"]["iso"], "newDeadline": c["deadline"]["iso"],
                   "extensionDays": (new - old).total_seconds() / 86400})
    if new > old:
        return {**result, "status": "clear", "reason": "This explicitly linked correction extends the submission deadline; not a late change without extension."}
    # Date-only publication can fall anywhere within this timezone envelope.
    earliest, latest = published - timedelta(hours=14), published + timedelta(days=1, hours=14)
    if not (old - timedelta(days=7) <= earliest and latest <= old):
        return {**result, "reason": "Publication day is not wholly inside the seven-day pre-deadline window."}
    # Source/path metadata differs between versions: compare only substantive fields.
    def criteria(e):
        return [{k: x.get(k) for k in ("type", "name", "description", "formula", "parameters")} for x in e.get("awardCriteria", [])]
    title_changed = bool(c.get("lotTitle") and p.get("lotTitle") and c["lotTitle"] != p["lotTitle"])
    criteria_changed = bool(c.get("awardCriteria") and p.get("awardCriteria") and criteria(c) != criteria(p))
    if not (title_changed or criteria_changed):
        return {**result, "reason": "No substantive title/award-criteria change established for this lot; document changes were not reviewed."}
    return {**result, "status": "signal", "reason": "Lot title or award criteria changed within seven days before the prior deadline, with no extension. Editorial check, not a legal breach."}
