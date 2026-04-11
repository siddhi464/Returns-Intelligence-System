"""
generate_data.py — Synthetic WSI Sentinel datasets (CSV + JSON).
Run: python generate_data.py
"""

import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ── Product master rows (full catalog schema) ────────────────────────────────
PRODUCT_ROWS = [
    {
        "sku_id": "WE-TBL-04",
        "product_name": "Mid-Century Dining Table",
        "brand": "West Elm",
        "category": "Tables",
        "sub_category": "Dining",
        "price": 899.0,
        "currency": "USD",
        "materials": "Solid oak, steel hardware",
        "finish": "Warm Walnut",
        "color": "Brown",
        "style": "Mid-Century",
        "dimensions_length": 72,
        "dimensions_width": 36,
        "dimensions_height": 30,
        "weight": 95.0,
        "components": "Top,Legs,Hinges,Apron",
        "assembly_required": True,
        "supplier_id": "SUP-4402",
        "manufacturing_location": "Vietnam",
        "warranty_period": 24,
        "launch_date": "2024-03-01",
        "discontinued_flag": False,
        "region": "West",
    },
    {
        "sku_id": "WE-TABLE-88",
        "product_name": "Classic Dining Table",
        "brand": "West Elm",
        "category": "Tables",
        "sub_category": "Dining",
        "price": 640.0,
        "currency": "USD",
        "materials": "Oak veneer",
        "finish": "Warm Walnut",
        "color": "Brown",
        "style": "Traditional",
        "dimensions_length": 68,
        "dimensions_width": 38,
        "dimensions_height": 30,
        "weight": 78.0,
        "components": "Top,Legs,Stretcher",
        "assembly_required": True,
        "supplier_id": "SUP-2201",
        "manufacturing_location": "USA",
        "warranty_period": 12,
        "launch_date": "2023-01-15",
        "discontinued_flag": False,
        "region": "West",
    },
    {
        "sku_id": "WE-SOFA-22",
        "product_name": "Mid-Century Sofa",
        "brand": "West Elm",
        "category": "Seating",
        "sub_category": "Sofa",
        "price": 1200.0,
        "currency": "USD",
        "materials": "Polyester blend, hardwood frame",
        "finish": "Slate Blue",
        "color": "Blue",
        "style": "Mid-Century",
        "dimensions_length": 84,
        "dimensions_width": 36,
        "dimensions_height": 34,
        "weight": 120.0,
        "components": "Frame,Cushions,Legs",
        "assembly_required": False,
        "supplier_id": "SUP-1100",
        "manufacturing_location": "Mexico",
        "warranty_period": 24,
        "launch_date": "2022-09-01",
        "discontinued_flag": False,
        "region": "East",
    },
    {
        "sku_id": "WE-CHAIR-05",
        "product_name": "Luxe Velvet Armchair",
        "brand": "West Elm",
        "category": "Seating",
        "sub_category": "Chair",
        "price": 420.0,
        "currency": "USD",
        "materials": "Velvet, brass legs",
        "finish": "Antique Brass",
        "color": "Brass",
        "style": "Modern",
        "dimensions_length": 32,
        "dimensions_width": 34,
        "dimensions_height": 32,
        "weight": 28.0,
        "components": "Seat,Back,Legs",
        "assembly_required": True,
        "supplier_id": "SUP-3303",
        "manufacturing_location": "China",
        "warranty_period": 12,
        "launch_date": "2023-06-01",
        "discontinued_flag": False,
        "region": "South",
    },
    {
        "sku_id": "WE-DESK-11",
        "product_name": "Modernist Writing Desk",
        "brand": "West Elm",
        "category": "Storage",
        "sub_category": "Desk",
        "price": 580.0,
        "currency": "USD",
        "materials": "Oak, metal drawer slides",
        "finish": "Natural Oak",
        "color": "Natural",
        "style": "Modern",
        "dimensions_length": 48,
        "dimensions_width": 24,
        "dimensions_height": 30,
        "weight": 55.0,
        "components": "Top,Drawers,Legs,Hinges",
        "assembly_required": True,
        "supplier_id": "SUP-2201",
        "manufacturing_location": "Vietnam",
        "warranty_period": 12,
        "launch_date": "2023-02-10",
        "discontinued_flag": False,
        "region": "North",
    },
    {
        "sku_id": "WE-BED-33",
        "product_name": "Solid Wood King Bed",
        "brand": "West Elm",
        "category": "Bedroom",
        "sub_category": "Bed",
        "price": 1800.0,
        "currency": "USD",
        "materials": "Solid walnut",
        "finish": "Dark Walnut",
        "color": "Brown",
        "style": "Platform",
        "dimensions_length": 84,
        "dimensions_width": 80,
        "dimensions_height": 45,
        "weight": 185.0,
        "components": "Headboard,Frame,Slats,Hardware",
        "assembly_required": True,
        "supplier_id": "SUP-5500",
        "manufacturing_location": "Canada",
        "warranty_period": 36,
        "launch_date": "2022-11-01",
        "discontinued_flag": False,
        "region": "West",
    },
    {
        "sku_id": "WE-LAMP-07",
        "product_name": "Arc Floor Lamp",
        "brand": "West Elm",
        "category": "Lighting",
        "sub_category": "Floor",
        "price": 260.0,
        "currency": "USD",
        "materials": "Metal, marble base",
        "finish": "Brushed Gold",
        "color": "Gold",
        "style": "Modern",
        "dimensions_length": 18,
        "dimensions_width": 18,
        "dimensions_height": 78,
        "weight": 22.0,
        "components": "Base,Arc,Shade,Hardware",
        "assembly_required": True,
        "supplier_id": "SUP-6601",
        "manufacturing_location": "China",
        "warranty_period": 12,
        "launch_date": "2024-01-20",
        "discontinued_flag": False,
        "region": "East",
    },
    {
        "sku_id": "WE-SHELF-14",
        "product_name": "Floating Shelf Unit",
        "brand": "West Elm",
        "category": "Storage",
        "sub_category": "Shelf",
        "price": 340.0,
        "currency": "USD",
        "materials": "Engineered wood",
        "finish": "White Oak",
        "color": "White",
        "style": "Minimal",
        "dimensions_length": 48,
        "dimensions_width": 12,
        "dimensions_height": 72,
        "weight": 35.0,
        "components": "Shelves,Brackets,Hardware",
        "assembly_required": True,
        "supplier_id": "SUP-2201",
        "manufacturing_location": "USA",
        "warranty_period": 12,
        "launch_date": "2023-08-01",
        "discontinued_flag": False,
        "region": "South",
    },
    {
        "sku_id": "WE-RUG-99",
        "product_name": "Hand-Loomed Wool Rug",
        "brand": "West Elm",
        "category": "Rugs",
        "sub_category": "Area",
        "price": 490.0,
        "currency": "USD",
        "materials": "Wool",
        "finish": "Terracotta",
        "color": "Orange",
        "style": "Bohemian",
        "dimensions_length": 96,
        "dimensions_width": 60,
        "dimensions_height": 0.5,
        "weight": 40.0,
        "components": "Rug body",
        "assembly_required": False,
        "supplier_id": "SUP-7700",
        "manufacturing_location": "India",
        "warranty_period": 12,
        "launch_date": "2023-04-01",
        "discontinued_flag": False,
        "region": "North",
    },
    {
        "sku_id": "WE-MIRROR-3",
        "product_name": "Arched Brass Mirror",
        "brand": "West Elm",
        "category": "Decor",
        "sub_category": "Mirror",
        "price": 320.0,
        "currency": "USD",
        "materials": "Glass, brass frame",
        "finish": "Antique Brass",
        "color": "Brass",
        "style": "Modern",
        "dimensions_length": 28,
        "dimensions_width": 1,
        "dimensions_height": 42,
        "weight": 18.0,
        "components": "Glass,Frame,Hanging hardware",
        "assembly_required": False,
        "supplier_id": "SUP-8801",
        "manufacturing_location": "China",
        "warranty_period": 12,
        "launch_date": "2023-10-01",
        "discontinued_flag": False,
        "region": "West",
    },
    {
        "sku_id": "WE-BENCH-21",
        "product_name": "Entryway Storage Bench",
        "brand": "West Elm",
        "category": "Seating",
        "sub_category": "Bench",
        "price": 510.0,
        "currency": "USD",
        "materials": "Leather, pine frame",
        "finish": "Cognac Leather",
        "color": "Brown",
        "style": "Transitional",
        "dimensions_length": 48,
        "dimensions_width": 18,
        "dimensions_height": 20,
        "weight": 42.0,
        "components": "Seat,Hinges,Storage box",
        "assembly_required": True,
        "supplier_id": "SUP-2201",
        "manufacturing_location": "Vietnam",
        "warranty_period": 12,
        "launch_date": "2023-05-01",
        "discontinued_flag": False,
        "region": "East",
    },
]

SKU_BY_ID = {p["sku_id"]: p for p in PRODUCT_ROWS}

ISSUE_MAP = {
    "WE-TBL-04": {
        "dominant": "quality_issue",
        "return_rate": 0.35,
        "notes": [
            "Table arrived, leg snapped when I stood it up",
            "joint on leg feels weak",
            "hinge hardware stripped during assembly",
            "surface scratch on top",
        ],
        "reviews": ["leg joint failed first week", "beautiful but leg cracked", "wobble on one leg"],
    },
    "WE-TABLE-88": {
        "dominant": "color_mismatch",
        "return_rate": 0.38,
        "notes": [
            "colour looked different in real life",
            "looks grey not warm brown",
            "warmer in the photo than in person",
        ],
        "reviews": ["colour is not what I expected", "looks grey not warm brown as shown"],
    },
    "WE-SOFA-22": {
        "dominant": "size_confusion",
        "return_rate": 0.28,
        "notes": ["too big for my living room", "much larger than expected", "sofa is huge compared to the listing"],
        "reviews": ["bigger than expected", "love the sofa but wrong size for me"],
    },
    "WE-CHAIR-05": {
        "dominant": "color_mismatch",
        "return_rate": 0.30,
        "notes": ["brass looks too yellow in person", "finish looks cheap not antique"],
        "reviews": ["finish looks different than photo"],
    },
    "WE-DESK-11": {
        "dominant": "quality_issue",
        "return_rate": 0.18,
        "notes": ["wobbly leg", "drawer doesn't close smoothly", "slight scratch on arrival"],
        "reviews": ["good desk but had scratches", "drawer mechanism is stiff"],
    },
    "WE-BED-33": {
        "dominant": "size_confusion",
        "return_rate": 0.22,
        "notes": ["headboard too tall", "didn't fit through door", "larger than I imagined"],
        "reviews": ["bed is stunning but very large"],
    },
    "WE-LAMP-07": {
        "dominant": "personal_reason",
        "return_rate": 0.12,
        "notes": ["changed my mind on the style", "cheap lamp not worth return shipping", "arrived broken, not worth fixing"],
        "reviews": ["nice lamp", "good quality"],
    },
    "WE-SHELF-14": {
        "dominant": "color_mismatch",
        "return_rate": 0.20,
        "notes": ["more yellow than white", "not the right white for my walls"],
        "reviews": ["slightly yellow tint not pure white"],
    },
    "WE-RUG-99": {
        "dominant": "color_mismatch",
        "return_rate": 0.25,
        "notes": ["much more orange than terracotta", "colour is off from photos"],
        "reviews": ["love the rug but colour is very orange"],
    },
    "WE-MIRROR-3": {
        "dominant": "quality_issue",
        "return_rate": 0.15,
        "notes": ["frame had minor dent", "slight imperfection in glass"],
        "reviews": ["beautiful mirror", "minor quality issue on arrival"],
    },
    "WE-BENCH-21": {
        "dominant": "personal_reason",
        "return_rate": 0.14,
        "notes": ["no longer needed", "moved house", "cancelled renovation project"],
        "reviews": ["lovely bench", "great quality leather"],
    },
}

RETURN_REASONS_MAP = {
    "color_mismatch": "does_not_match_description",
    "size_confusion": "wrong_size",
    "quality_issue": "defective_or_damaged",
    "personal_reason": "no_longer_needed",
}

CITIES_BY_REGION = {
    "West": [("Los Angeles", "90001", "CA"), ("San Francisco", "94102", "CA"), ("Seattle", "98101", "WA"), ("Portland", "97201", "OR"), ("Denver", "80202", "CO")],
    "East": [("New York", "10001", "NY"), ("Boston", "02101", "MA"), ("Philadelphia", "19101", "PA"), ("Miami", "33101", "FL"), ("Atlanta", "30301", "GA")],
    "South": [("Houston", "77001", "TX"), ("Dallas", "75201", "TX"), ("Austin", "78701", "TX"), ("Nashville", "37201", "TN"), ("Charlotte", "28201", "NC")],
    "North": [("Chicago", "60601", "IL"), ("Minneapolis", "55401", "MN"), ("Detroit", "48201", "MI"), ("Milwaukee", "53202", "WI"), ("Columbus", "43201", "OH")],
}

CONTACT_REASONS = ["color_inquiry", "size_confusion", "quality_complaint", "shipping_issue", "general_inquiry", "warranty_claim"]
CONTACT_TRANSCRIPTS = {
    "color_inquiry": [
        "Customer asked why the colour looks different from website photos.",
        "Customer upset that the finish doesn't match the listing.",
    ],
    "size_confusion": [
        "Customer couldn't visualise scale from photos.",
        "Customer said item is too big for their space.",
    ],
    "quality_complaint": [
        "Customer reported leg snapped during setup. Escalated to quality.",
        "Complaint about wobbly leg. Agent sent replacement hardware.",
        "Warranty claim: structural failure at joint confirmed.",
    ],
    "shipping_issue": [
        "Package delayed by 3 days. Agent applied discount code.",
        "Item arrived with damaged box.",
    ],
    "general_inquiry": [
        "Customer asked about care instructions.",
        "Inquiry about warranty coverage.",
    ],
    "warranty_claim": [
        "Formal warranty claim filed for broken hinge assembly batch 402.",
        "Structural failure documented; replacement parts shipped.",
    ],
}

PARTS = ["Leg", "Hinge", "Drawer slide", "Top panel", "Hardware kit", ""]


def random_date(start_days_ago=180):
    delta = timedelta(days=random.randint(0, start_days_ago))
    return (datetime.now() - delta).strftime("%Y-%m-%d")


def generate_returns(n=520):
    rows = []
    for i in range(n):
        product = random.choice(PRODUCT_ROWS)
        sku = product["sku_id"]
        region = product["region"]
        info = ISSUE_MAP.get(sku, ISSUE_MAP["WE-TABLE-88"])

        if random.random() < 0.70:
            dominant = info["dominant"]
            note = random.choice(info["notes"])
        else:
            dominant = random.choice(list(RETURN_REASONS_MAP.keys()))
            note = random.choice(
                ["changed my mind", "ordered by mistake", "colour slightly different", "size not right"]
            )

        if random.random() < 0.08:
            dominant = "personal_reason"
            note = random.choice(
                ["cancelled event", "home renovation cancelled", "moved house", "no longer need it"]
            )

        city, zip_c, state = random.choice(CITIES_BY_REGION[region])
        order_date = datetime.now() - timedelta(days=random.randint(10, 200))
        ret_date = order_date + timedelta(days=random.randint(1, 45))

        rows.append(
            {
                "return_id": f"R{str(i+1).zfill(4)}",
                "order_id": f"ORD{str(random.randint(10000, 99999))}",
                "sku_id": sku,
                "return_reason": RETURN_REASONS_MAP.get(dominant, "no_longer_needed"),
                "return_note": note,
                "return_condition": random.choice(["like_new", "open_box", "damaged", "defective"]),
                "return_date": ret_date.strftime("%Y-%m-%d"),
                "days_to_return": (ret_date - order_date).days,
                "city": city,
                "state": state,
                "region": region,
                "zip_code": int(zip_c),
                "cost_of_return": round(random.uniform(120, 220), 2),
            }
        )
    return pd.DataFrame(rows)


def generate_reviews(n=450):
    rows = []
    for i in range(n):
        product = random.choice(PRODUCT_ROWS)
        sku = product["sku_id"]
        info = ISSUE_MAP.get(sku, ISSUE_MAP["WE-TABLE-88"])
        base_rating = 4.5 - info["return_rate"] * 5
        rating = max(1, min(5, round(base_rating + random.gauss(0, 0.8))))

        if rating <= 2 and random.random() < 0.7:
            text = random.choice(info["reviews"])
        else:
            text = random.choice(
                [
                    "Great quality!",
                    "Love this piece.",
                    "Exactly as described.",
                    "Fast delivery and beautiful product.",
                ]
            )

        rows.append(
            {
                "review_id": f"REV{str(i+1).zfill(4)}",
                "sku_id": sku,
                "rating": rating,
                "review_text": text,
                "images_attached": random.choice([True, False, False]),
                "review_date": random_date(),
            }
        )
    return pd.DataFrame(rows)


def generate_contacts(n=320, return_ids: list[str] | None = None):
    rows = []
    return_ids = return_ids or []
    for i in range(n):
        product = random.choice(PRODUCT_ROWS)
        sku = product["sku_id"]
        reason = random.choice(CONTACT_REASONS)
        transcript = random.choice(CONTACT_TRANSCRIPTS.get(reason, CONTACT_TRANSCRIPTS["general_inquiry"]))
        resolutions = [
            "return_initiated",
            "exchange_offered",
            "discount_applied",
            "information_provided",
            "escalated_to_team",
            "resolved_no_action",
        ]
        rid = random.choice(return_ids) if return_ids and random.random() < 0.35 else ""
        rows.append(
            {
                "contact_id": f"CS{str(i+1).zfill(4)}",
                "return_id": rid,
                "sku_id": sku,
                "contact_reason": reason,
                "transcript": transcript,
                "resolution": random.choice(resolutions),
                "part_requested": random.choice(PARTS) or "None",
                "contact_date": random_date(),
            }
        )
    return pd.DataFrame(rows)


def generate_logistics_meta():
    rows = []
    for region_list in CITIES_BY_REGION.values():
        for city, zip_c, _st in region_list:
            rows.append(
                {
                    "zip_code": int(zip_c),
                    "shipping_rate": round(random.uniform(32.0, 68.0), 2),
                    "cluster_density": random.choice([1, 1, 2, 2, 3, 4, 5]),
                }
            )
    for _ in range(30):
        z = random.randint(10000, 99999)
        rows.append(
            {
                "zip_code": z,
                "shipping_rate": round(random.uniform(35.0, 75.0), 2),
                "cluster_density": random.choice([1, 2, 3, 4]),
            }
        )
    return pd.DataFrame(rows)


def generate_warehouse_status():
    return [
        {
            "hub_id": "WH001",
            "name": "Olive Branch, MS",
            "current_capacity": 62,
            "labor_availability": 6,
            "lat": 34.96,
            "lon": -89.83,
            "processing_rate": 1.0,
            "demand_score": {"WE-TBL-04": 9, "WE-TABLE-88": 8},
        },
        {
            "hub_id": "WH002",
            "name": "Reno, NV",
            "current_capacity": 78,
            "labor_availability": 5,
            "lat": 39.53,
            "lon": -119.81,
            "processing_rate": 1.05,
            "demand_score": {"WE-SOFA-22": 7},
        },
        {
            "hub_id": "WH003",
            "name": "Baltimore, MD",
            "current_capacity": 55,
            "labor_availability": 7,
            "lat": 39.29,
            "lon": -76.61,
            "processing_rate": 0.98,
            "demand_score": {"WE-BED-33": 6},
        },
        {
            "hub_id": "WH004",
            "name": "Dallas, TX",
            "current_capacity": 82,
            "labor_availability": 6,
            "lat": 32.78,
            "lon": -96.80,
            "processing_rate": 1.0,
            "demand_score": {"WE-LAMP-07": 4},
        },
        {
            "hub_id": "WH005",
            "name": "Columbus, OH",
            "current_capacity": 88,
            "labor_availability": 4,
            "lat": 39.96,
            "lon": -82.99,
            "processing_rate": 1.02,
            "demand_score": {"WE-DESK-11": 5},
        },
    ]


def generate_product_master_json():
    out = []
    for p in PRODUCT_ROWS:
        out.append(
            {
                "sku_id": p["sku_id"],
                "dimensions": {
                    "length_in": p["dimensions_length"],
                    "width_in": p["dimensions_width"],
                    "height_in": p["dimensions_height"],
                },
                "weight_lb": p["weight"],
                "components": (p["components"] or "").split(","),
            }
        )
    return out


if __name__ == "__main__":
    import os

    os.makedirs("data", exist_ok=True)

    returns = generate_returns(520)
    return_id_list = returns["return_id"].tolist()
    reviews = generate_reviews(450)
    contacts = generate_contacts(320, return_id_list)
    product_master = pd.DataFrame(PRODUCT_ROWS)
    logistics = generate_logistics_meta()
    wh = generate_warehouse_status()

    returns.to_csv("data/returns.csv", index=False)
    reviews.to_csv("data/reviews.csv", index=False)
    contacts.to_csv("data/cs_contacts.csv", index=False)
    product_master.to_csv("data/product_master.csv", index=False)
    logistics.to_csv("data/logistics_meta.csv", index=False)

    legacy_products = product_master[["sku_id", "product_name", "category", "finish", "price", "region"]].rename(
        columns={"product_name": "name"}
    )
    legacy_products.to_csv("data/products.csv", index=False)

    with open("data/warehouse_status.json", "w", encoding="utf-8") as f:
        json.dump(wh, f, indent=2)
    with open("data/wms_live.json", "w", encoding="utf-8") as f:
        json.dump(wh, f, indent=2)

    with open("data/product_master.json", "w", encoding="utf-8") as f:
        json.dump(generate_product_master_json(), f, indent=2)

    print("Generated: returns.csv, reviews.csv, cs_contacts.csv, product_master.csv,")
    print("         logistics_meta.csv, warehouse_status.json, wms_live.json, product_master.json, products.csv")
