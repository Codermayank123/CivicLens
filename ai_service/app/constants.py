CATEGORIES = [
    "pothole",
    "garbage",
    "broken_streetlight",
    "water_leakage",
    "damaged_road",
    "drainage_problem",
    "electrical_hazard",
    "sanitation",
    "public_safety",
    "traffic_signal",
    "other",
]

URGENCY_KEYWORDS = {
    "high": [
        "dangerous", "urgent", "emergency", "hazard", "risk", "accident",
        "collapse", "flood", "fire", "electrocution", "injury", "broken",
    ],
    "medium": [
        "overflow", "blocked", "damaged", "leaking", "crack", "pothole",
        "garbage", "smell", "noise", "complaint",
    ],
    "low": [
        "minor", "small", "cosmetic", "faded", "paint", "aesthetic",
    ],
}

CATEGORY_DEPARTMENTS = {
    "pothole": "Public Works Department",
    "damaged_road": "Public Works Department",
    "garbage": "Sanitation Department",
    "sanitation": "Sanitation Department",
    "broken_streetlight": "Electrical Department",
    "electrical_hazard": "Electrical Department",
    "water_leakage": "Water Supply Department",
    "drainage_problem": "Water Supply Department",
    "traffic_signal": "Traffic Management",
    "public_safety": "Public Safety",
}
