"""Parser voor CSV-exports uit de ING app / Mijn ING.

Ondersteunt zowel het huidige formaat (puntkomma, "Datum";"Naam / Omschrijving";...)
als het oudere komma-formaat en de Engelstalige export.
"""
import csv
import hashlib
import io
from datetime import datetime

# Kolomnamen (lowercase) -> interne veldnaam
HEADER_ALIASES = {
    "datum": "date", "date": "date",
    "naam / omschrijving": "name", "name / description": "name",
    "rekening": "account", "account": "account",
    "tegenrekening": "counter_account", "counterparty": "counter_account",
    "code": "code",
    "af bij": "direction", "debit/credit": "direction",
    "bedrag (eur)": "amount", "amount (eur)": "amount",
    "mutatiesoort": "mutation_type", "transaction type": "mutation_type",
    "mededelingen": "description", "notifications": "description",
    "saldo na mutatie": "balance", "resulting balance": "balance",
    "tag": "tag",
}


class ParseError(Exception):
    pass


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ParseError("Kan de tekstcodering van het bestand niet bepalen.")


def _parse_amount(value: str) -> float:
    v = (value or "").strip().replace(" ", "")
    if not v:
        return 0.0
    if "," in v and "." in v:  # 1.234,56
        v = v.replace(".", "").replace(",", ".")
    else:
        v = v.replace(",", ".")
    return float(v)


def _parse_date(value: str) -> str:
    v = value.strip()
    for fmt in ("%Y%m%d", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ParseError(f"Onbekend datumformaat: {value!r}")


def parse_ing_csv(raw: bytes) -> list:
    text = _decode(raw)
    first_line = text.splitlines()[0] if text else ""
    delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        raise ParseError("Het bestand is leeg.")

    columns = {}
    for idx, col in enumerate(header):
        key = HEADER_ALIASES.get(col.strip().strip('"').lower())
        if key:
            columns[key] = idx
    missing = {"date", "name", "direction", "amount"} - columns.keys()
    if missing:
        raise ParseError(
            "Dit lijkt geen ING-export te zijn (kolommen ontbreken: "
            + ", ".join(sorted(missing)) + ")."
        )

    def get(row, key):
        idx = columns.get(key)
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    transactions = []
    seen = {}
    for row in reader:
        if not row or not any(c.strip() for c in row):
            continue
        amount = _parse_amount(get(row, "amount"))
        direction = get(row, "direction").lower()
        if direction in ("af", "debit"):
            amount = -abs(amount)
        else:
            amount = abs(amount)
        balance_raw = get(row, "balance")
        tx = {
            "date": _parse_date(get(row, "date")),
            "name": get(row, "name"),
            "account": get(row, "account"),
            "counter_account": get(row, "counter_account"),
            "code": get(row, "code"),
            "amount": round(amount, 2),
            "mutation_type": get(row, "mutation_type"),
            "description": get(row, "description"),
            "balance": _parse_amount(balance_raw) if balance_raw else None,
        }
        # Deterministische sleutel zodat overlappende exports geen dubbelingen geven.
        # Identieke regels (zelfde dag, bedrag, winkel) krijgen een volgnummer.
        base = "|".join(str(tx[k]) for k in (
            "date", "name", "account", "counter_account", "amount", "description", "balance"))
        seen[base] = seen.get(base, 0) + 1
        tx["hash"] = hashlib.sha256(f"{base}|{seen[base]}".encode()).hexdigest()
        transactions.append(tx)
    return transactions
