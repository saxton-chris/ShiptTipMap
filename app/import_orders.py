"""
Import Shipt order history from CSV exports into shipt_tracker.db.

Expects one CSV per spreadsheet tab (e.g. data/feb-mar.csv,
data/apr-may.csv, data/jun-jul.csv, data/aug-sep.csv) with columns:
    Date, Order Number, Preferred Member, Name/Customer Name, Address,
    Store, Order Amount, Tip, Tip Percent, Tip Logged, Notes

Run stores.py (seed_stores.py) BEFORE this script — orders link to
stores by foreign key, so stores must already exist.

Usage:
    python import_orders.py
"""

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Customer, Order, Store

engine = create_engine("sqlite:///tip_map.db")
SessionLocal = sessionmaker(bind=engine)

# Add each CSV export here as you create them.
CSV_FILES = [
    "data/feb-mar.csv",
    "data/apr-may.csv",
    "data/jun-jul.csv",
    "data/aug-sep.csv",
]

# Map known spelling/spacing variants (lowercased, whitespace-collapsed)
# to the canonical store name as seeded in stores.py. Add new entries
# here whenever the "unmatched store names" report below turns one up.
STORE_ALIASES = {
    "hyvee - shakopee": "Hy-Vee - Shakopee",
    "hy-vee - shakopee": "Hy-Vee - Shakopee",
    "lunds & byerlys - chanhassen": "Lunds & Byerly - Chanhassen",
    "lunds & byerly - chanhassen": "Lunds & Byerly - Chanhassen",
    "total wine- chanhassen": "Total Wine - Chanhassen",
    "total wine - chanhassen": "Total Wine - Chanhassen",
    "total wine - chanhasssen": "Total Wine - Chanhassen",  # typo seen in sheet
    "cub - chanhassen": "Cub - Chanhassen",
}


def normalize_whitespace(value: str) -> str:
    """Collapse newlines/extra spaces and strip leading/trailing whitespace."""
    return " ".join(value.split())


def normalize_key(value: str) -> str:
    """Lowercased, whitespace-normalized version used only for matching."""
    return normalize_whitespace(value).lower()


def parse_date(raw: str):
    return datetime.strptime(raw.strip(), "%m/%d/%Y").date()


def parse_money(raw: str) -> float | None:
    raw = (raw or "").strip().replace("$", "").replace(",", "")
    if not raw:
        return None
    return float(raw)


def parse_bool(raw: str) -> bool:
    return (raw or "").strip().upper() == "TRUE"


def get_or_create_customer(db, name: str, address: str) -> Customer:
    """Match on name + address together, case/whitespace-insensitive.
    Same name at a different address is treated as a different customer
    (handles duplicate names like multiple "John S" entries).
    """
    name = normalize_whitespace(name)
    address = normalize_whitespace(address)
    name_key = normalize_key(name)
    address_key = normalize_key(address)

    existing = db.query(Customer).all()
    for customer in existing:
        if (
            normalize_key(customer.name) == name_key
            and normalize_key(customer.address) == address_key
        ):
            return customer

    customer = Customer(name=name, address=address)
    db.add(customer)
    db.flush()  # get customer.id without committing yet
    return customer


def get_store_id(db, raw_name: str, store_cache: dict, unmatched: set) -> int | None:
    raw_name = normalize_whitespace(raw_name)
    key = normalize_key(raw_name)

    # Already resolved this exact string before? Reuse the cached id.
    if key in store_cache:
        return store_cache[key]

    # Try the alias map first (handles known spelling variants).
    canonical = STORE_ALIASES.get(key, raw_name)
    canonical_key = normalize_key(canonical)

    store = db.query(Store).filter(Store.name == canonical).first()
    if store is None:
        # Fall back to a case-insensitive scan in case casing differs
        # from what's in the table but isn't in the alias map.
        for s in db.query(Store).all():
            if normalize_key(s.name) == canonical_key:
                store = s
                break

    if store is None:
        unmatched.add(raw_name)
        return None

    store_cache[key] = store.id
    return store.id


def import_file(db, path: str, store_cache: dict, unmatched_stores: set, rejected: list):
    if not Path(path).exists():
        print(f"  Skipping {path} — file not found.")
        return 0

    imported = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # header is row 1
            order_number_raw = (row.get("Order Number") or row.get("Order Number ") or "").strip()
            if not order_number_raw:
                continue  # blank order number = dead formula row, skip silently

            try:
                order_number = int(order_number_raw)
            except ValueError:
                rejected.append((path, row_num, "non-numeric order number", row))
                continue

            total_amount = parse_money(row.get("Order Amount"))
            if total_amount is None:
                rejected.append((path, row_num, "missing order amount", row))
                continue

            name = row.get("Name") or row.get("Customer Name") or ""
            address = row.get("Address") or ""
            if not name.strip() or not address.strip():
                rejected.append((path, row_num, "missing name or address", row))
                continue

            store_id = get_store_id(db, row.get("Store", ""), store_cache, unmatched_stores)
            if store_id is None:
                rejected.append((path, row_num, "unmatched store", row))
                continue

            # Skip if this order number already exists (re-running the
            # script, or the same order appearing in more than one file).
            if db.query(Order).filter(Order.order_number == order_number).first():
                continue

            customer = get_or_create_customer(db, name, address)

            if parse_bool(row.get("Preferred Member")) and not customer.preferred:
                customer.preferred = True

            db.add(
                Order(
                    order_number=order_number,
                    order_date=parse_date(row["Date"]),
                    customer_id=customer.id,
                    store_id=store_id,
                    total_amount=total_amount,
                    tip_amount=parse_money(row.get("Tip") or row.get("Tips")),
                    tip_logged=parse_bool(row.get("Tip Logged")),
                    notes=normalize_whitespace(row.get("Notes") or "") or None,
                )
            )
            imported += 1

    db.commit()
    return imported


def main():
    db = SessionLocal()
    store_cache: dict[str, int] = {}
    unmatched_stores: set[str] = set()
    rejected: list[tuple] = []

    try:
        total_imported = 0
        for path in CSV_FILES:
            print(f"Importing {path}...")
            count = import_file(db, path, store_cache, unmatched_stores, rejected)
            print(f"  {count} orders imported.")
            total_imported += count

        print(f"\nDone. {total_imported} total orders imported.")

        if unmatched_stores:
            print(f"\n{len(unmatched_stores)} unmatched store name(s) — "
                  f"add these to STORE_ALIASES or the stores table:")
            for name in sorted(unmatched_stores):
                print(f"  - {name!r}")

        if rejected:
            print(f"\n{len(rejected)} row(s) rejected:")
            for path, row_num, reason, row in rejected:
                print(f"  - {path} row {row_num}: {reason} "
                      f"(order#: {row.get('Order Number', '?')})")

    finally:
        db.close()


if __name__ == "__main__":
    main()