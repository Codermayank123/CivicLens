"""Development-only MongoDB seed data.

Never run this against a production database. The script is additive and uses
upserts so it does not drop or overwrite existing collections.
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.core import hash_password
from app.core.mongo import model_to_doc
from app.database import close_db, get_database, init_db
from app.models.department import ComplaintCategory, Department
from app.models.user import User

DEPARTMENTS = [
    ("Public Works Department", "PWD", "Roads, bridges, and public infrastructure"),
    ("Water Supply Department", "WSD", "Water supply, drainage, and sewage"),
    ("Electrical Department", "ELEC", "Street lighting and electrical infrastructure"),
    ("Sanitation Department", "SAN", "Garbage collection and cleanliness"),
    ("Traffic Management", "TRF", "Traffic signals and road markings"),
    ("Public Safety", "PSF", "Public safety hazards and emergency infrastructure"),
]

CATEGORIES = [
    ("Pothole", "pothole", "PWD", "road", "#E74C3C"),
    ("Damaged Road", "damaged_road", "PWD", "road", "#C0392B"),
    ("Garbage", "garbage", "SAN", "trash", "#27AE60"),
    ("Sanitation", "sanitation", "SAN", "trash", "#229954"),
    ("Broken Streetlight", "broken_streetlight", "ELEC", "lightbulb", "#F39C12"),
    ("Electrical Hazard", "electrical_hazard", "ELEC", "bolt", "#D68910"),
    ("Water Leakage", "water_leakage", "WSD", "droplet", "#3498DB"),
    ("Drainage Problem", "drainage_problem", "WSD", "droplet", "#2874A6"),
    ("Public Safety Issue", "public_safety", "PSF", "shield", "#9B59B6"),
    ("Traffic Signal Problem", "traffic_signal", "TRF", "traffic-cone", "#E74C3C"),
    # Fallback when AI cannot map a specific category; officers triage these.
    ("Needs Officer Review", "other", "PWD", "help-circle", "#4B205B"),
]


async def seed_database() -> None:
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("Demo seed data is disabled in production")
    await init_db()
    db = get_database()
    department_ids: dict[str, str] = {}
    for name, code, description in DEPARTMENTS:
        existing = await db.departments.find_one({"code": code})
        if existing:
            department_ids[code] = str(existing["_id"])
        else:
            department = Department(name=name, code=code, description=description)
            await db.departments.insert_one(model_to_doc(department))
            department_ids[code] = department.id
    infrastructure = await db.complaint_categories.find_one({"slug": "infrastructure"})
    if not infrastructure:
        infrastructure_model = ComplaintCategory(name="Infrastructure", slug="infrastructure", description="Public infrastructure issues and services", icon="building", color="#4B205B", display_order=0)
        await db.complaint_categories.insert_one(model_to_doc(infrastructure_model))
        infrastructure = {"_id": infrastructure_model.id}
    for index, (name, slug, dept_code, icon, color) in enumerate(CATEGORIES, start=1):
        await db.complaint_categories.update_one(
            {"slug": slug},
            {"$set": {"name": name, "department_id": department_ids[dept_code], "icon": icon, "color": color, "parent_id": str(infrastructure["_id"],), "display_order": index, "is_active": True}},
            upsert=True,
        )
    demo_password = hash_password("Demo@12345")
    users = [
        ("citizen@example.com", "Rajesh Kumar (Demo Citizen)", ["citizen"], None),
        ("officer@example.com", "Anita Sharma (Demo Officer)", ["officer"], department_ids["PWD"]),
        ("fieldstaff@example.com", "Vikram Singh (Demo Field Staff)", ["field_staff"], department_ids["PWD"]),
        ("admin@example.com", "Meera Patel (Demo Administrator)", ["admin"], None),
    ]
    for email, name, roles, department_id in users:
        # Development accounts must remain usable after schema or hash changes.
        # This is deliberately limited to the four named non-production accounts.
        demo_user = model_to_doc(User(email=email, full_name=name, password_hash=demo_password, roles=roles, department_id=department_id, city="Delhi", is_verified=True, email_verified=True, identity_verified=True))
        demo_user.pop("_id", None)
        # The development database has a legacy non-sparse unique phone index;
        # do not write null phone values into demo accounts.
        demo_user.pop("phone", None)
        await db.users.update_one(
            {"email": email},
            {"$set": demo_user, "$unset": {"phone": ""}},
            # Remove any legacy null field before the unique index evaluates it.
            upsert=True,
        )
    print("Seeded development departments, categories, and demo accounts.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed_database())
