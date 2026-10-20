"""Classify evidence cited in Ukrainian AMCU bid-rigging judgments.

Pure Python, no external dependencies. Labels describe AMCU's asserted evidence,
including findings disputed by a bidder or rejected by a court; they do not
describe whether the court upheld the decision. No inference from a party's
ordinary contact details, telephone conversations, or generic investigation lists.

IP uses the narrower procurement definition: a common IP for bid submission,
procurement registration, or auction/system access. Bank/tax/email-only IP use
is excluded. Contact details in bank/tax records do count. A negative label means
that this evidence was not identified in the supplied judgments, not that AMCU
necessarily lacked it. Same-building findings count even with different rooms
when explicitly treated as a common address in the decision.

Run this file to classify case-texts.json and score evidence_validation.json.
"""

import json
import re
from pathlib import Path


def _normalize(text):
    text = text.lower().replace("\u00ad", "")
    text = re.sub(r"[’‘`ʼ]", "'", text)
    text = re.sub(r"[‐‑–—−]", "-", text)
    # Latin, Cyrillic and mixed-script spellings all occur in judgments.
    text = re.sub(r"(?<!\w)[iіи][pр](?=\s*[- ]?\s*адрес)", "ip", text)
    # Preserve paragraph boundaries for attribution and bank/tax-only IP scope.
    text = re.sub(r"[^\S\n]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text)


_PRECEDENT = re.compile(
    r"(?:верховн\w*\s+суд\w*\s+(?:у|в)\s+(?:постанов|справ)|"
    r"у\s+постанов[^\n]{0,120}верховного\s+суду|"
    r"за\s+висновками\s+верховного\s+суду\s+у\s+названих\s+справах)"
)


def _prepare(text):
    text = _normalize(text)
    # Factual summaries of OTHER cases are often quoted as legal authority.
    # Mask the paragraph, keeping offsets/paragraph boundaries intelligible.
    text = "\n".join(" " if _PRECEDENT.search(p) else p for p in text.split("\n"))
    # A stock statement of the legal test, sometimes formatted as a multi-line
    # list whose attribution to Supreme Court precedent appears at the end.
    return re.sub(
        r"(?m)^[^\n]*змагальність\s+виключається\s+шляхом\s+встановлення[^\n]*:\s*\n"
        r"(?:\s*-[^\n]*(?:\n|$)){1,20}", "\n", text
    )


_WORD = r"[а-яіїєґa-z'\-]+"
_TOKEN = rf"(?:{_WORD}|[«\"][^«»\";\n]{{1,100}}[»\"])"
# Equality must be tied to the particular evidence, not simply nearby in a
# sentence that mentions common employees, similar documents, etc.
_SAME = (
    r"(?:однаков\w*|одинаков\w*|ідентичн\w*|идентичн\w*|"
    r"спільн(?:ий|ого|ому|им|ім|а|ої|ою|у|е|і|их|ими|ість|ості)"
    r"|один(?:\s+(?:і|й|и))?(?:\s+т(?:ой|от))?(?:\s+(?:ж|же|сам\w*)){0,2}"
    r"|одн(?:а|е|і|их|ими|у|ою|ією|ієї|ий|им|ого|ому)(?:\s+(?:і|й))?"
    r"(?:\s+т(?:ой|ого|ому|им|ією|ієї|і|их|ими|у|а|е))?"
    r"(?:\s+(?:ж|же|сам\w*)){0,2}"
    r"|т(?:ой|ого|ому|им|ією|ієї|і|их|ими|у|а|е)\s+(?:ж|же|сам\w*))"
)
_PHONE = r"(?:телефон(?:и|ів|у|ом|ами|ах|а)?\b|(?:контактн\w*\s*)?номер\w*\s+(?:(?:мобільн|контактн)\w*\s+)?телефон\w*|телефонн\w*\s+(?:номер\w*|засоб\w*\s+зв'язку))"
_EMAIL = (
    r"(?:електронн\w*\s+(?:поштов\w*\s+)?(?:пошт\w*|адрес\w*|скринь\w*)"
    r"|(?:адрес\w*|скринь\w*|засоб\w*)\s+електронн\w*\s+пошт\w*"
    r"|поштов\w*\s+електронн\w*\s+(?:адрес\w*|скринь\w*)"
    r"|электронн\w*\s+(?:почт\w*|адрес\w*|почтов\w*\s+ящик\w*)"
    r"|адрес\w*\s+электронн\w*\s+почт\w*"
    r"|e\s*-?\s*mail\w*)"
)
_IP = r"ip\s*-?\s*адрес\w*"
_PHYSICAL = r"(?:адрес(?:а|и|ою|у|і|ами|ах)?\b|місцезнаходжен\w*|місце\w*\s+(?:знаходжен|розташуван)\w*|(?:офісн\w*\s+|нежитлов\w*\s+)?приміщен\w*|офіс(?:у|і|ом|и|ів|ами|ах)?\b)"
_FILL = r"(?:фактичн\w*|юридичн\w*|поштов\w*|контактн\w*|мобільн\w*|стаціонарн\w*|реєстраційн\w*|фіксован\w*|зовнішн\w*|статичн\w*|динамічн\w*|електронн\w*|номер\w*|засоб\w*|телефонн\w*)"
_GAP = rf"(?:\s+{_FILL}){{0,4}}\s*"
_COINCIDE = r"(?:збіга\w*|співпада\w*|співпали|співпало|ідентичн\w*|однаков\w*)"


def _compile(noun):
    return [
        re.compile(rf"\b{_SAME}{_GAP}(?:-\s*)?{noun}"),
        re.compile(rf"\b(?:збіг|співпадіння|ідентичність|спільність)\s+(?:{_FILL}\s+){{0,3}}{noun}"),
        re.compile(rf"\b{noun}(?:\s+{_TOKEN}){{0,5}}\s+{_COINCIDE}"),
    ]


_PATTERNS = {
    "contact": _compile(rf"(?:{_PHONE}|{_EMAIL})"),
    "address": _compile(_PHYSICAL),
    "ip": _compile(_IP),
}
# Explicit 'jointly used a phone/email', allowing an intervening verb.
_PATTERNS["contact"].append(re.compile(
    rf"\bспільно\s+(?:використов\w*|корист\w*)(?:\s+{_FILL}){{0,3}}\s+(?:{_PHONE}|{_EMAIL})"
))
_PATTERNS["address"].append(re.compile(
    rf"\bспільно\s+(?:використов\w*|оренд\w*|корист\w*)\s+{_PHYSICAL}"
))
_PATTERNS["ip"].extend([
    # Implicit equality: plural bidders + a single specified IP for their bids.
    re.compile(rf"\bучасники(?:\s+торгів)?[^;\n]{{0,100}}?"
               rf"(?:створювали|подавали|завантажували|заходили|здійснювали\s+вхід)"
               rf"[^;\n]{{0,100}}?\s+з\s+{_IP}\s+(?:номер_\d+|\d+(?:\.\d+){{3}})"),
    re.compile(rf"{_IP},\s+яка\s+належала\s+іншому\s+конкуренту,\s+"
               rf"з\s+якої\s+останній\s+подавав\s+свою\s+тендерну\s+пропозицію"),
    re.compile(rf"{_SAME}\s+(?:і\s+тим\s+ж\s+)?комп'ютер\w*\s+та\s+{_IP}"),
])

_PROCUREMENT_USE = re.compile(
    r"(?:пода\w*|подан\w*|завантаж\w*|створ\w*|надсил\w*|реєстрац\w*)"
    r"[^;\n]{0,100}(?:тендерн\w*|пропозиц\w*|заяв\w*|майданчик\w*)|"
    r"(?:тендерн\w*|пропозиц\w*)[^;\n]{0,90}(?:пода\w*|подан\w*|завантаж\w*|створ\w*)|"
    r"(?:вхід|вход\w*|вихід|заход\w*|авторизац\w*)[^;\n]{0,80}"
    r"(?:аукціон\w*|майданчик\w*|закупів\w*|prozorro|прозор\w*)|"
    r"ip\s*-?\s*адрес\w*\s+при\s+участі\s+[ув]\s+торгах"
)
_OTHER_IP_USE = re.compile(r"податков|звітн|звітів|банків|клієнт\s*-\s*банк|поштов|витяг|єдр|реєстру")

# Organization names are used only to veto a clearly identified affiliate pair.
# Unresolved names/pronouns remain eligible; there is no case-number lookup.
_ORG = re.compile(
    r"\b(?:тзов|тов|прат|пат|пп|пф|пвкф|кп|дп|вкп|"
    r"товариств\w*\s+з\s+обмеженою\s+відповідальністю|"
    r"(?:приватн|державн|комунальн)\w*\s+(?:підприємств\w*|фірм\w*)|"
    r"(?:приватн\w*\s+|публічн\w*\s+)?акціонерн\w*\s+товариств\w*)\s*[«\"]"
    r"(?:(?:компанія|во|бк|апб|нвф|тпк|науково-виробнича\s+фірма)\s*[«\"])?"
    r"([^«»\"\n]{2,100})[»\"]"
)
_UNQUOTED_ORG = re.compile(
    r"\b(?:тов|тзов|пп|дп|кп)\s+(?:тпк\s+)?([а-яіїєґ][а-яіїєґ0-9\-]{2,})"
)


def _org_names(fragment):
    quoted = {re.sub(r"\s+", " ", m.group(1)).strip(" '-")
              for m in _ORG.finditer(fragment)}
    unquoted = {m.group(1) for m in _UNQUOTED_ORG.finditer(fragment)}
    unquoted -= {"використовує", "використовували", "листом", "зазначило", "було",
                 "було", "здійснює", "надало", "щодо", "таким", "при", "яке"}
    return quoted | unquoted


_FOP = re.compile(r"\b(?:фоп|фізичн\w*\s+особ\w*\s*-\s*підприєм\w*)\s+(особа_\d+|[а-яіїєґ'\-]{4,})")


def _entity_names(fragment):
    # The first seven surname characters tolerate common case inflections.
    return _org_names(fragment) | {"fop:" + m.group(1)[:7] for m in _FOP.finditer(fragment)}


def _bidder_names(text):
    names = set()
    # A finding that named firms' actions were a violation is stronger than
    # frequency: affiliates can be mentioned more often than actual bidders.
    for pattern in (
        r"(?:визнано|визнав|визнала|визнати)[^\n]{0,60}?(?:дії|дій|що)\s+([^\n]{1,650}?)(?:порушенням|щодо|під\s+час|антиконкурент)",
        r"(?:дії|дій)\s+([^\n]{1,500}?)(?:полягали|підтверджуються|щодо\s+узгодження)",
        r"(?:дії|дій)\s+([^\n]{1,500}?)\s+визнано\s+(?:антиконкурентними|узгодженими)",
        r"визнання\s+ді[йї]\s+([^\n]{1,500}?)\s+антиконкурентними",
        r"(?:за\s+позовом\s*:?|за\s+позовами\s*:?|третя\s+особа[^\n:]{0,110}[:\-])\s*([^\n]{1,350})",
        r"(?:учасниками\s+торгів\s+(?:є|були)|учасники\s+торгів\s*:)\s*([^\n]{1,450})",
    ):
        for m in re.finditer(pattern, text):
            names.update(_entity_names(m.group(1)))
    return names


def _clause(text, start, end, limit=900):
    left = max(text.rfind("\n", 0, start), text.rfind(";", 0, start), start - limit)
    right = min([p for p in (text.find("\n", end), text.find(";", end), end + limit)
                 if p >= 0])
    return text[left + 1:right]

_PARTICIPANTS = re.compile(
    r"учасник|товариств|підприємств|відповідач|позивач|торг|тендер|конкурент|"
    r"\bтов\b|\bтзов\b|\bпп\b|\bфоп\b|суб'єкт|комітет|відділен|амку|амк\b"
)
_FINDING = re.compile(
    r"використ|корист|зазнач|вказа|встанов|свідч|підтвердж|збіг|збіга|"
    r"співпад|спільн|однаков|знаход|розташ|реєстр|оренд|надсил|подан|подач"
)
_NEGATIVE = re.compile(
    r"(?:не\s+(?:було\s+)?(?:встановлено|виявлено|підтверджено|доведено)|"
    r"відсутність|відсутні|відсутня|відсутнє)\s+(?:факт\w*\s+|відомост\w*\s+|"
    r"доказ\w*\s+|щодо\s+|про\s+|використання\s+|наявності\s+){0,4}$"
)
_INQUIRY = re.compile(
    r"(?:наявності\s*(?:/|або|чи|та|\()\s*відсутності\)?|наявність\s*(?:/|або|чи|та|\()\s*відсутність\)?|"
    r"(?:запит|вимог)\w*[^.;]{0,65}(?:надати|надання)\s+інформаці\w*[^.;]{0,60})$"
)


def _accepted(text, match, field, bidders=None):
    start, end = match.span()
    phrase = match.group()
    before = text[max(0, start - 180):start]
    after = text[end:end + 180]
    local = text[max(0, start - 400):end + 400]
    if _NEGATIVE.search(before) or _INQUIRY.search(before):
        return False
    clause = _clause(text, start, end)
    if (re.search(r"(?:досліджув\w*|досліджено|перевірял\w*|вивчал\w*|аналізувал\w*)"
                  r"[^.;\n]{0,120}$", before)
            and not re.search(r"встановлено|виявлено|підтверджено|свідчить", clause)):
        return False
    # Reverse equality patterns must not turn an explicit difference into a hit.
    if re.search(r"\bне\s+(?:збіг|збіга|співпад|співпа)", phrase):
        return False
    if not _PARTICIPANTS.search(local):
        return False
    if field == "contact":
        # Calls between different numbers are a different type of evidence.
        if re.search(r"телефонн\w*\s+(?:розмов|з'єднан|дзвін|переговор)", phrase):
            return False
        if re.search(r"(?:суд\w*|адвокат\w*|представник\w*)\s*$", before[-70:]):
            return False
        if re.match(r"\s+(?:суду|судді|адвоката|представника)\b", after):
            return False
        if re.search(_COINCIDE + r"$", phrase) and re.match(
                r"\s+з\s+(?:назв|прізвищ|ім'ям|імен|датою)", after):
            return False
    elif field == "address":
        # 'Адреса' may be a network address, email, or court addressee.
        if re.search(r"\b(?:ip|електронн\w*)\s*-?\s*адрес", phrase):
            return False
        if re.search(r"(?:ip\s*-?\s*|електронн\w*\s+)$", before):
            return False
        if re.match(r"\s+(?:електронн\w*|e-?mail|мережі|суду)\b", after):
            return False
        if re.search(r"адрес\w*\s+(?:електронн|пошт\w*\s+скринь)", phrase):
            return False
        if not _FINDING.search(local):
            return False
        if re.search(r"не\s+встановив[^.;\n]{0,220}$", before):
            return False
        if re.search(r"не\s+(?:долучено|надано)\s+доказів[^;\n]{0,100}$", before):
            return False
        if re.search(r"відмінне\s+місцезнаходження\s+за\s*$", before):
            return False
        if re.search(r"а\s+зумовлене\s+веденням\s+ними\s+господарської\s+діяльності\s+за\s*$", before):
            return False
        if (re.match(r",\s*номер[ау]\s+телефон", after)
                and re.search(r"реєстраці|комп'ютер", local)
                and not re.search(r"юридичн|фактичн|приміщен|поштов", phrase)):
            return False
        if bidders:
            subject = re.split(r"при\s+цьому[, ]|отже[, ]", before)[-1]
            subject = re.split(r"[;\n]", subject)[-1]
            named = _entity_names(subject + " " + phrase + after[:120])
            # Ignore an explicit shared address whose subject is an affiliate,
            # a common founder's firm, or one bidder plus its parent company.
            if named and named - bidders and len(named & bidders) < 2:
                return False
    elif field == "ip":
        if _OTHER_IP_USE.search(clause) and not _PROCUREMENT_USE.search(clause):
            return False
        if re.search(r"(?:може|можуть)\s+бути\s+(?:надан|присвоєн)|"
                     r"декількома\s+споживачами|невизначен\w*\s+кількост", clause):
            if not _PROCUREMENT_USE.search(clause):
                return False
    return True


def evidence_matches(text):
    """Diagnostic spans in normalized text; not required for classification."""
    text = _prepare(text)
    bidders = _bidder_names(text)
    found = {field: [] for field in _PATTERNS}
    for field, patterns in _PATTERNS.items():
        seen = set()
        for pattern in patterns:
            for match in pattern.finditer(text):
                if match.span() not in seen and _accepted(text, match, field, bidders):
                    found[field].append({
                        "phrase": match.group(),
                        "context": text[max(0, match.start() - 180):match.end() + 240],
                    })
                    seen.add(match.span())
    return found


def classify(text):
    """Return contact/address/ip/any_link bools for concatenated judgments."""
    text = _prepare(text)
    bidders = _bidder_names(text)
    result = {}
    for field, patterns in _PATTERNS.items():
        result[field] = any(
            _accepted(text, match, field, bidders)
            for pattern in patterns for match in pattern.finditer(text)
        )
    result["any_link"] = any(result.values())
    return result


def main():
    root = Path(__file__).resolve().parent
    texts = json.loads((root / "case-texts.json").read_text())
    results = {case: classify(text) for case, text in texts.items()}
    (root / "case-evidence.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    )
    print("Cases:", len(results))
    print("Counts:", {key: sum(row[key] for row in results.values())
                      for key in ("contact", "address", "ip", "any_link")})
    validation = root / "evidence_validation.json"
    if validation.exists():
        labels = json.loads(validation.read_text())
        print("Manual validation cases:", len(labels))
        print("Stratified manual sample; includes cases used for rule refinement.")
        report = {
            "cases": len(results),
            "counts": {key: sum(row[key] for row in results.values())
                       for key in ("contact", "address", "ip", "any_link")},
            "validation_cases": len(labels),
            "sampling": "46 cases stratified by initial 3-field predictions (seed 20261020), "
                        "then 16 fresh cases stratified by revised predictions (seed 48101). "
                        "Unweighted, small-sample metrics; sample used for rule refinement, "
                        "not an independent estimate of population accuracy.",
            "ip_scope": "procurement submission/registration/auction access; "
                        "bank/tax/email-only or registry-extract-only IP use excluded",
            "metrics": {},
        }
        for field in ("contact", "address", "ip", "any_link"):
            tp = fp = fn = tn = 0
            for row in labels:
                actual = row[field] if field != "any_link" else any(
                    row[key] for key in ("contact", "address", "ip"))
                predicted = results[row["case"]][field]
                tp += predicted and actual
                fp += predicted and not actual
                fn += not predicted and actual
                tn += not predicted and not actual
            precision = tp / (tp + fp) if tp + fp else None
            recall = tp / (tp + fn) if tp + fn else None
            report["metrics"][field] = dict(precision=precision, recall=recall,
                                            tp=tp, fp=fp, fn=fn, tn=tn)
            precision_str = f"{precision:.3f}" if precision is not None else "n/a"
            recall_str = f"{recall:.3f}" if recall is not None else "n/a"
            print(f"{field}: precision={precision_str} recall={recall_str} "
                  f"TP={tp} FP={fp} FN={fn} TN={tn}")
        (root / "evidence_validation_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
