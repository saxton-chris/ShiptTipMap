"""
One-time seed script to populate the stores table.

Run this after create_db.py has generated shipt_tracker.db, and before
importing your order history — orders reference stores by foreign key,
so stores need to exist first.

Usage:
    python seed_stores.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Store

engine = create_engine("sqlite:///tip_map.db")
SessionLocal = sessionmaker(bind=engine)

# Cleaned/deduplicated list of stores pulled from your spreadsheet.
# A few names appeared with inconsistent spelling/spacing across rows
# (e.g. "HyVee" vs "Hy-Vee", "Lunds & Byerlys" vs "Lunds & Byerly",
# "Total Wine" vs "Total Wine- Chanhassen") -- normalized to one
# canonical spelling per store here. Add to this list any time a new
# store shows up that isn't already covered.
STORE_NAMES = [
    "Target - Chaska",
    "Target - Waconia",
    "Target - Chanhassen",
    "Cub - Chaska",
    "Cub - Chanhassen",
    "Cub - Shorewood",
    "Lunds & Byerly - Chanhassen",
    "Hy-Vee - Shakopee",
    "Total Wine - Chanhassen",
    "Petco - Chaska",
    "Kowalski's - Excelsior",
    "OfficeMax - Chanhassen",
]

def seed_stores():
    db = SessionLocal()
    try:
        existing_names = {name for (name,) in db.query(Store.name).all()}
        added = 0

        for name in STORE_NAMES:
            if name in existing_names:
                continue
            db.add(Store(name=name))
            added += 1

        db.commit()
        print(f"Added {added} new store(s). {len(STORE_NAMES) - added} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_stores()