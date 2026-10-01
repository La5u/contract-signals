"""Pseudonymise supplier identifiers that are a natural person's national ID.

Publishers release these numbers lawfully (Colombian cédulas in SECOP II, Ukrainian individual
tax numbers in Prozorro, Chilean RUNs and Paraguayan cédula-based RUCs), but this project does
not need to republish them: identity matching only needs a stable key. Each such identifier
becomes "masked-" + 16 hex characters of SHA-256 over "<type>:<id>", the same in every run and
every dataset, so repetition and concentration checks still match the same person.

This is data minimisation, not secrecy: the raw snapshots under data/*/raw/ keep the exact
public responses, and the number space is small enough to be enumerated. Company identifiers
(NIT, EDRPOU, company RUT or RUC, SIREN, NIF, CUI, IČO) are left as published.
"""
import hashlib

PERSON_DOCUMENT_TYPES = {"Cédula de Ciudadanía", "Cédula de Extranjería", "RNOKPP"}
CHILE_COMPANY_RUT_FROM = 50_000_000      # Chilean company RUTs start at 50 million; lower numbers are persons' RUNs
PARAGUAY_COMPANY_RUC_FROM = 80_000_000   # Paraguayan company RUCs start at 80 million; lower ones derive from a cédula


def is_personal(identifier_type, identifier):
    value = str(identifier or "")
    if value.startswith("masked-"):
        return False
    if identifier_type in PERSON_DOCUMENT_TYPES:
        return True
    if identifier_type == "CL-RUT":
        number = value[:-1]
        return number.isdigit() and int(number) < CHILE_COMPANY_RUT_FROM
    if identifier_type == "RUC" and value.startswith("PY-RUC-"):
        number = value.split("-")[2]
        return number.isdigit() and int(number) < PARAGUAY_COMPANY_RUC_FROM
    return False


def mask(identifier_type, identifier):
    if not is_personal(identifier_type, identifier):
        return identifier
    return "masked-" + hashlib.sha256(f"{identifier_type}:{identifier}".encode("utf-8")).hexdigest()[:16]


def mask_ids(identifiers):
    return [{**s, "id": mask(s.get("identifierType"), s.get("id"))} for s in identifiers or []]
