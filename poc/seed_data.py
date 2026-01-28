"""Seed the rate database with sample routes.

Run: PYTHONPATH=. python -m poc.seed_data
"""

from datetime import date, timedelta

from poc.database import SessionLocal, create_tables
from poc.db_models import Rate, _uuid

SEED_RATES = [
    {
        "carrier_name": "Emirates SkyCargo",
        "mode": "AIR",
        "origin_port": "SIN",
        "destination_port": "PHC",
        "currency": "USD",
        "rate_per_unit": 20.0,
        "unit": "KG",
        "minimum_charge": 500.0,
        "dg_surcharge_pct": 15.0,
        "notes": "Singapore to Port Harcourt air freight",
    },
    {
        "carrier_name": "Emirates SkyCargo",
        "mode": "AIR",
        "origin_port": "SIN",
        "destination_port": "LOS",
        "currency": "USD",
        "rate_per_unit": 18.0,
        "unit": "KG",
        "minimum_charge": 500.0,
        "dg_surcharge_pct": 15.0,
        "notes": "Singapore to Lagos air freight",
    },
    {
        "carrier_name": "British Airways Cargo",
        "mode": "AIR",
        "origin_port": "LHR",
        "destination_port": "PHC",
        "currency": "USD",
        "rate_per_unit": 22.0,
        "unit": "KG",
        "minimum_charge": 400.0,
        "dg_surcharge_pct": 15.0,
        "notes": "London Heathrow to Port Harcourt air freight",
    },
    {
        "carrier_name": "British Airways Cargo",
        "mode": "AIR",
        "origin_port": "LHR",
        "destination_port": "LOS",
        "currency": "USD",
        "rate_per_unit": 20.0,
        "unit": "KG",
        "minimum_charge": 400.0,
        "dg_surcharge_pct": 15.0,
        "notes": "London Heathrow to Lagos air freight",
    },
    {
        "carrier_name": "Maersk",
        "mode": "SEA",
        "origin_port": "SIN",
        "destination_port": "PHC",
        "currency": "USD",
        "rate_per_unit": 100.0,
        "unit": "CBM",
        "minimum_charge": 1000.0,
        "dg_surcharge_pct": 20.0,
        "notes": "Singapore to Port Harcourt sea freight",
    },
    {
        "carrier_name": "MSC",
        "mode": "SEA",
        "origin_port": "MER",
        "destination_port": "PHC",
        "currency": "USD",
        "rate_per_unit": 120.0,
        "unit": "CBM",
        "minimum_charge": 1200.0,
        "dg_surcharge_pct": 20.0,
        "notes": "Mersin to Port Harcourt sea freight",
    },
]


def seed():
    create_tables()
    db = SessionLocal()
    try:
        existing = db.query(Rate).filter(Rate.source == "SEED").count()
        if existing > 0:
            print(f"Database already has {existing} seeded rates. Skipping.")
            return

        today = date.today()
        valid_to = today + timedelta(days=30)

        for rate_data in SEED_RATES:
            rate = Rate(
                id=_uuid(),
                valid_from=today,
                valid_to=valid_to,
                source="SEED",
                status="ACTIVE",
                **rate_data,
            )
            db.add(rate)

        db.commit()
        print(f"Seeded {len(SEED_RATES)} rates successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
