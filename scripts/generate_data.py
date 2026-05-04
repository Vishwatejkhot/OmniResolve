import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

UK_FIRST_NAMES = [
    "James", "Oliver", "Harry", "Jack", "George", "Noah", "Charlie", "Jacob",
    "Alfie", "Freddie", "Amelia", "Olivia", "Isla", "Ava", "Mia", "Isabella",
    "Sophie", "Poppy", "Grace", "Lily", "Mohammed", "Aisha", "Priya", "Fatima",
    "Ravi", "Anjali", "Chen", "Wei", "Yuki", "Elena", "Stefan", "Aoife", "Cian",
]
UK_LAST_NAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson",
    "Thomas", "Roberts", "Johnson", "Walker", "Wright", "Robinson", "Thompson",
    "White", "Hughes", "Edwards", "Green", "Hall", "Lewis", "Harris", "Clarke",
    "Patel", "Khan", "Singh", "Ali", "Ahmed", "Shah", "Begum", "Sharma", "Kumar",
]
UK_CITIES = [
    "London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool",
    "Bristol", "Sheffield", "Edinburgh", "Leicester", "Coventry", "Bradford",
    "Cardiff", "Nottingham", "Newcastle", "Belfast", "Brighton", "Southampton",
]

SELLERS = [
    {"id": "seller_001", "name": "TechHub Electronics",      "dispute_rate": 0.031, "refund_rate": 0.072, "fraud_signals": 0, "category": "electronics"},
    {"id": "seller_002", "name": "FastFashion Ltd",           "dispute_rate": 0.089, "refund_rate": 0.143, "fraud_signals": 1, "category": "clothing"},
    {"id": "seller_003", "name": "HomeComfort Furniture",     "dispute_rate": 0.044, "refund_rate": 0.065, "fraud_signals": 0, "category": "furniture"},
    {"id": "seller_004", "name": "ToyWorld Direct",           "dispute_rate": 0.028, "refund_rate": 0.051, "fraud_signals": 0, "category": "toys"},
    {"id": "seller_005", "name": "BookBarn Online",           "dispute_rate": 0.012, "refund_rate": 0.038, "fraud_signals": 0, "category": "books"},
    {"id": "seller_006", "name": "GadgetZone UK",             "dispute_rate": 0.062, "refund_rate": 0.098, "fraud_signals": 2, "category": "electronics"},
    {"id": "seller_007", "name": "SportsPro Direct",          "dispute_rate": 0.035, "refund_rate": 0.067, "fraud_signals": 0, "category": "clothing"},
    {"id": "seller_008", "name": "ElectroBargains",           "dispute_rate": 0.121, "refund_rate": 0.187, "fraud_signals": 4, "category": "electronics"},
    {"id": "seller_009", "name": "Luxe Living",               "dispute_rate": 0.019, "refund_rate": 0.041, "fraud_signals": 0, "category": "furniture"},
    {"id": "seller_010", "name": "KidsKingdom",               "dispute_rate": 0.023, "refund_rate": 0.049, "fraud_signals": 0, "category": "toys"},
    {"id": "seller_011", "name": "MegaMarket Online",         "dispute_rate": 0.076, "refund_rate": 0.112, "fraud_signals": 3, "category": "general"},
    {"id": "seller_012", "name": "GreenLeaf Foods",           "dispute_rate": 0.041, "refund_rate": 0.063, "fraud_signals": 0, "category": "food"},
    {"id": "seller_013", "name": "PhotoPro Supplies",         "dispute_rate": 0.033, "refund_rate": 0.058, "fraud_signals": 0, "category": "electronics"},
    {"id": "seller_014", "name": "Cosy Home Stores",          "dispute_rate": 0.027, "refund_rate": 0.044, "fraud_signals": 0, "category": "furniture"},
    {"id": "seller_015", "name": "QuickShip Marketplace",     "dispute_rate": 0.098, "refund_rate": 0.154, "fraud_signals": 5, "category": "general"},
    {"id": "seller_016", "name": "PremiumThreads",            "dispute_rate": 0.015, "refund_rate": 0.031, "fraud_signals": 0, "category": "clothing"},
    {"id": "seller_017", "name": "AutoParts Express",         "dispute_rate": 0.053, "refund_rate": 0.088, "fraud_signals": 1, "category": "automotive"},
    {"id": "seller_018", "name": "NatureWell Supplements",    "dispute_rate": 0.068, "refund_rate": 0.102, "fraud_signals": 2, "category": "health"},
    {"id": "seller_019", "name": "ArtisanCrafts UK",          "dispute_rate": 0.021, "refund_rate": 0.037, "fraud_signals": 0, "category": "crafts"},
    {"id": "seller_020", "name": "ZapDeal Electronics",       "dispute_rate": 0.134, "refund_rate": 0.201, "fraud_signals": 6, "category": "electronics"},
]

PRODUCTS = [
    {"sku": "ELEC-001", "name": "Sony WH-1000XM5 Wireless Headphones",     "category": "electronics", "price_gbp": 279.99, "defect_rate": 0.018, "return_rate": 0.042, "seller_id": "seller_001"},
    {"sku": "ELEC-002", "name": "Apple AirPods Pro 2nd Generation",          "category": "electronics", "price_gbp": 229.00, "defect_rate": 0.012, "return_rate": 0.031, "seller_id": "seller_001"},
    {"sku": "ELEC-003", "name": "Samsung 65\" QLED 4K Smart TV",             "category": "electronics", "price_gbp": 899.00, "defect_rate": 0.009, "return_rate": 0.028, "seller_id": "seller_001"},
    {"sku": "ELEC-004", "name": "Dell XPS 15 Laptop 16GB RAM 512GB SSD",     "category": "electronics", "price_gbp": 1249.99, "defect_rate": 0.022, "return_rate": 0.038, "seller_id": "seller_013"},
    {"sku": "ELEC-005", "name": "Dyson V15 Detect Cordless Vacuum Cleaner",  "category": "electronics", "price_gbp": 449.99, "defect_rate": 0.031, "return_rate": 0.055, "seller_id": "seller_006"},
    {"sku": "ELEC-006", "name": "Nintendo Switch OLED Console",              "category": "electronics", "price_gbp": 299.99, "defect_rate": 0.014, "return_rate": 0.027, "seller_id": "seller_006"},
    {"sku": "ELEC-007", "name": "Fitbit Charge 6 Fitness Tracker",           "category": "electronics", "price_gbp": 119.99, "defect_rate": 0.041, "return_rate": 0.073, "seller_id": "seller_008"},
    {"sku": "ELEC-008", "name": "Canon EOS R50 Mirrorless Camera",           "category": "electronics", "price_gbp": 699.00, "defect_rate": 0.008, "return_rate": 0.021, "seller_id": "seller_013"},
    {"sku": "ELEC-009", "name": "Bose SoundLink Flex Bluetooth Speaker",     "category": "electronics", "price_gbp": 139.99, "defect_rate": 0.027, "return_rate": 0.048, "seller_id": "seller_008"},
    {"sku": "ELEC-010", "name": "Ring Video Doorbell Pro 2",                 "category": "electronics", "price_gbp": 199.99, "defect_rate": 0.035, "return_rate": 0.061, "seller_id": "seller_020"},
    {"sku": "CLTH-001", "name": "The North Face Waterproof Hiking Jacket",   "category": "clothing", "price_gbp": 189.99, "defect_rate": 0.011, "return_rate": 0.089, "seller_id": "seller_007"},
    {"sku": "CLTH-002", "name": "Nike Air Max 270 Running Trainers",          "category": "clothing", "price_gbp": 109.99, "defect_rate": 0.019, "return_rate": 0.112, "seller_id": "seller_007"},
    {"sku": "CLTH-003", "name": "Women's Cashmere V-Neck Jumper",             "category": "clothing", "price_gbp": 79.99, "defect_rate": 0.023, "return_rate": 0.098, "seller_id": "seller_016"},
    {"sku": "CLTH-004", "name": "Men's Slim Fit Chinos 32W 32L",              "category": "clothing", "price_gbp": 39.99, "defect_rate": 0.028, "return_rate": 0.076, "seller_id": "seller_002"},
    {"sku": "CLTH-005", "name": "Adidas Ultraboost 22 Running Shoes",         "category": "clothing", "price_gbp": 149.99, "defect_rate": 0.016, "return_rate": 0.094, "seller_id": "seller_007"},
    {"sku": "CLTH-006", "name": "Levi's 501 Original Fit Jeans",              "category": "clothing", "price_gbp": 69.99, "defect_rate": 0.009, "return_rate": 0.082, "seller_id": "seller_016"},
    {"sku": "CLTH-007", "name": "Columbia Powder Lite Hooded Jacket",         "category": "clothing", "price_gbp": 84.99, "defect_rate": 0.014, "return_rate": 0.067, "seller_id": "seller_002"},
    {"sku": "FURN-001", "name": "3-Seater Chesterfield Velvet Sofa in Teal",  "category": "furniture", "price_gbp": 549.00, "defect_rate": 0.041, "return_rate": 0.033, "seller_id": "seller_003"},
    {"sku": "FURN-002", "name": "Solid Oak 6-Drawer Chest of Drawers",        "category": "furniture", "price_gbp": 329.99, "defect_rate": 0.029, "return_rate": 0.026, "seller_id": "seller_003"},
    {"sku": "FURN-003", "name": "King Size Memory Foam Mattress 1500 Pocket", "category": "furniture", "price_gbp": 449.99, "defect_rate": 0.018, "return_rate": 0.039, "seller_id": "seller_009"},
    {"sku": "FURN-004", "name": "Glass and Steel Extending Dining Table",     "category": "furniture", "price_gbp": 299.00, "defect_rate": 0.052, "return_rate": 0.044, "seller_id": "seller_003"},
    {"sku": "FURN-005", "name": "Ergonomic Office Chair Lumbar Support",      "category": "furniture", "price_gbp": 219.99, "defect_rate": 0.037, "return_rate": 0.051, "seller_id": "seller_014"},
    {"sku": "FURN-006", "name": "Floating Wall-Mounted TV Unit 180cm",        "category": "furniture", "price_gbp": 189.99, "defect_rate": 0.044, "return_rate": 0.038, "seller_id": "seller_014"},
    {"sku": "TOYS-001", "name": "LEGO Technic Bugatti Chiron 3599 Pieces",    "category": "toys", "price_gbp": 279.99, "defect_rate": 0.007, "return_rate": 0.028, "seller_id": "seller_004"},
    {"sku": "TOYS-002", "name": "Barbie Dreamhouse 2024 Edition",              "category": "toys", "price_gbp": 159.99, "defect_rate": 0.021, "return_rate": 0.041, "seller_id": "seller_010"},
    {"sku": "TOYS-003", "name": "Hot Wheels Ultimate Garage Playset",          "category": "toys", "price_gbp": 89.99, "defect_rate": 0.018, "return_rate": 0.034, "seller_id": "seller_004"},
    {"sku": "TOYS-004", "name": "VTech Touch and Learn Activity Desk",         "category": "toys", "price_gbp": 49.99, "defect_rate": 0.024, "return_rate": 0.046, "seller_id": "seller_010"},
    {"sku": "BOOK-001", "name": "Atomic Habits by James Clear (Hardcover)",    "category": "books", "price_gbp": 14.99, "defect_rate": 0.003, "return_rate": 0.018, "seller_id": "seller_005"},
    {"sku": "BOOK-002", "name": "The Thursday Murder Club (Hardcover)",         "category": "books", "price_gbp": 12.99, "defect_rate": 0.004, "return_rate": 0.021, "seller_id": "seller_005"},
    {"sku": "FOOD-001", "name": "Organic Protein Powder Chocolate 2kg",        "category": "health", "price_gbp": 34.99, "defect_rate": 0.009, "return_rate": 0.027, "seller_id": "seller_018"},
    {"sku": "FOOD-002", "name": "Vitamin D3 + K2 Supplement 365 Capsules",     "category": "health", "price_gbp": 19.99, "defect_rate": 0.006, "return_rate": 0.019, "seller_id": "seller_018"},
]

DAMAGE_TEMPLATES = [
    (
        "I received my {product} (order {order_id}) on {delivery_date} and was extremely disappointed "
        "to find significant damage. The outer packaging had clearly been crushed during transit — "
        "there was a large dent on one side and the box had been taped over by what appeared to be "
        "the courier. Upon opening, the {product} itself had a cracked {part} and {fault}. "
        "I have photographic evidence of both the packaging and the product damage. "
        "I purchased this for £{price} on {purchase_date} and this is clearly not of satisfactory quality "
        "under Section 9 of the Consumer Rights Act 2015. I am requesting a full replacement or refund."
    ),
    (
        "My {product} arrived on {delivery_date} in an unacceptable condition. The item was described "
        "as brand new but it arrived with {fault} and {part} was visibly damaged. I ordered this as a "
        "gift and it was embarrassing to present it in this state. "
        "The order reference is {order_id}. Under Section 9 of the Consumer Rights Act 2015, "
        "goods must be of satisfactory quality. This item clearly is not. "
        "I am requesting a replacement to be sent within 7 days, failing which I will require a full refund."
    ),
    (
        "I am writing to formally dispute my order {order_id} for {product}. "
        "When the item arrived on {delivery_date}, I noticed immediately that {fault}. "
        "The {part} does not function as described and the item is not fit for purpose under Section 10 "
        "of the Consumer Rights Act 2015. I paid £{price} for this item and expect it to work correctly. "
        "I have attempted to contact customer support twice with no satisfactory response. "
        "Please arrange a replacement or process a full refund within 14 days."
    ),
    (
        "Formal complaint regarding order {order_id} — {product}. "
        "Delivery date: {delivery_date}. Issue: {fault}. "
        "The {part} is broken/defective and the product does not match the description on the listing. "
        "Under the Consumer Rights Act 2015, Section 11, goods must match their description. "
        "The listing stated the item was brand new and fully functional. It arrived with {fault}. "
        "I want this resolved immediately. Options acceptable to me: full refund of £{price} "
        "or like-for-like replacement. I have photos and video evidence."
    ),
    (
        "I'm raising a dispute for a damaged {product} I received last {delivery_date}. "
        "The item (order {order_id}, £{price}) arrived with {fault}. "
        "The {part} was clearly broken before dispatch — this is not transit damage. "
        "I've attached photos showing the fault clearly. "
        "Section 9 Consumer Rights Act 2015 requires goods to be of satisfactory quality. "
        "A £{price} {product} arriving broken does not meet that standard. "
        "Requesting: (1) prepaid returns label, (2) full refund or replacement within 7 days."
    ),
]

NON_DELIVERY_TEMPLATES = [
    (
        "I placed an order for {product} on {purchase_date} (order {order_id}, £{price}). "
        "The estimated delivery was {expected_delivery}. It is now {today} and my item has not arrived. "
        "The tracking reference last updated on {last_scan_date} showing the parcel in {city} — "
        "it has not moved since. I have contacted the courier directly and they have confirmed "
        "the parcel appears to be lost. Under Section 28 of the Consumer Rights Act 2015, "
        "delivery must be made within 30 days. That deadline has now passed. "
        "I am requesting either immediate re-delivery or a full refund of £{price}."
    ),
    (
        "Non-delivery complaint — order {order_id}. "
        "I ordered {product} on {purchase_date} for £{price}. "
        "Promised delivery: {expected_delivery}. Current date: {today}. "
        "The tracking shows: 'Parcel in transit — {city} depot' since {last_scan_date} with no update. "
        "I have raised this with the courier ({courier}) who have opened a lost parcel investigation. "
        "They have told me to contact the seller for a refund or replacement. "
        "Under the Consumer Rights Act 2015, the seller is responsible for delivery. "
        "I require a full refund of £{price} or guaranteed re-delivery within 48 hours."
    ),
    (
        "My order {order_id} for {product} (£{price}) placed on {purchase_date} has not been delivered. "
        "Tracking shows the last scan was {last_scan_date} in {city}. "
        "The item is {days_overdue} days overdue. "
        "I have been patient but this is now unacceptable. "
        "The Consumer Rights Act 2015 Section 28 states goods must be delivered within 30 days "
        "unless a different period is agreed. No different period was agreed. "
        "Please arrange immediate redelivery or process a full refund. "
        "If not resolved within 7 days I will initiate a chargeback."
    ),
    (
        "I'm filing a formal non-delivery dispute for order {order_id}. "
        "Item: {product}. Purchase date: {purchase_date}. Value: £{price}. "
        "Tracking number: {order_id}-TRK. Last update: {last_scan_date}, {city}. "
        "The item was supposed to arrive by {expected_delivery}. "
        "It is now {days_overdue} days late and the courier website shows no movement. "
        "I need this resolved — either the item delivered or money refunded. "
        "I work from home and have been in every day. This item has not been attempted."
    ),
]

FRAUD_TEMPLATES = [
    (
        "I am reporting an unauthorised transaction on my account. "
        "Order {order_id} for {product} (£{price}) was placed on {purchase_date} without my knowledge or consent. "
        "I did not make this purchase. I have not visited this seller's website recently. "
        "I have already contacted my bank who have flagged this as potentially fraudulent. "
        "I am requesting: (1) immediate cancellation and full refund of £{price}, "
        "(2) an explanation of how this order was placed on my account, "
        "(3) details of the delivery address used. "
        "If this is not resolved within 48 hours I will report this to Action Fraud and Trading Standards."
    ),
    (
        "Fraudulent order on my account — urgent. "
        "I received an email confirmation for order {order_id} ({product}, £{price}) "
        "which I absolutely did not place. My account appears to have been compromised. "
        "I have since changed my password and enabled two-factor authentication. "
        "The order was placed on {purchase_date} from an IP address I don't recognise. "
        "Please cancel this order immediately, refund £{price} to my original payment method, "
        "and provide details of the security incident. "
        "I have also raised this with my card provider."
    ),
    (
        "I am raising a fraud dispute for order {order_id}. "
        "I was charged £{price} for {product} on {purchase_date} — this was not authorised by me. "
        "I have never heard of {seller_name} and have never placed an order with them. "
        "My payment details appear to have been used fraudulently. "
        "I require an immediate refund. "
        "Please also provide the delivery address for this order so I can share it with the police. "
        "I have already filed a report with Action Fraud (reference: TBC)."
    ),
    (
        "Unauthorised charge — order {order_id}, £{price}. "
        "This transaction for {product} dated {purchase_date} was not made by me. "
        "I was on holiday between {purchase_date} and {delivery_date} and could not have placed this order. "
        "My passport confirms I was abroad. "
        "This is clearly fraud. Refund required immediately. "
        "If not actioned within 24 hours I will dispute with my card issuer under Section 75 "
        "of the Consumer Credit Act 1974."
    ),
]

OTHER_TEMPLATES = [
    (
        "I am disputing order {order_id} for {product} (£{price}). "
        "The item I received does not match the product described in the listing. "
        "I ordered {product} but received a completely different item — the colour is wrong, "
        "the size is incorrect, and the model number differs from what was advertised. "
        "Under Section 11 of the Consumer Rights Act 2015, goods must match their description. "
        "This one does not. I am requesting the correct item to be sent or a full refund."
    ),
    (
        "Return and refund request for order {order_id}. "
        "I purchased {product} for £{price} on {purchase_date}. "
        "I returned the item via tracked post on {delivery_date} (tracking: {order_id}-RET) "
        "and the return was confirmed as received on {last_scan_date}. "
        "It has now been {days_overdue} days and I have not received my refund. "
        "Under your stated returns policy and the Consumer Rights Act 2015, "
        "refunds should be processed within 14 days of receipt of the returned item. "
        "Please process my refund of £{price} immediately."
    ),
    (
        "Billing error on order {order_id}. "
        "I was charged £{price} but the price at the time of purchase was clearly shown as "
        "£{discounted_price} with a promotional discount applied. "
        "I have a screenshot of the checkout showing the discounted price. "
        "I am disputing the overcharge of £{overcharge_amount}. "
        "Please either refund the difference or provide justification for the discrepancy."
    ),
    (
        "I am contacting you regarding order {order_id} for {product}. "
        "The item was advertised as compatible with my existing setup but it is not. "
        "I specifically asked in the product Q&A whether it would work with {product} "
        "and was told yes by the seller. It does not work. "
        "This constitutes a breach of Section 10 of the Consumer Rights Act 2015 "
        "(goods must be fit for particular purpose made known to the seller). "
        "I wish to return the item for a full refund of £{price}."
    ),
]

_PARTS_BY_CATEGORY = {
    "electronics": ["screen", "charging port", "battery", "casing", "speaker", "hinge", "connector", "lens"],
    "clothing": ["zip", "seam", "button", "strap", "sole", "lining", "collar", "hem"],
    "furniture": ["leg", "drawer runner", "hinge", "panel", "screw fitting", "glass top", "cushion foam"],
    "toys": ["wheel", "battery compartment", "clasp", "arm joint", "motor", "LED display"],
    "books": ["binding", "cover", "spine", "pages"],
    "health": ["seal", "lid", "packaging"],
    "automotive": ["fitting", "connector", "seal"],
    "crafts": ["clasp", "mechanism"],
    "general": ["casing", "connector"],
    "food": ["seal", "packaging"],
}

_FAULTS_BY_CATEGORY = {
    "electronics": [
        "the screen has a large crack running diagonally across it",
        "the device will not power on at all",
        "the charging port is bent and will not accept a cable",
        "the battery drains to zero within 20 minutes",
        "there are dead pixels across the top third of the display",
        "the right speaker produces no sound",
        "the hinge is broken and the lid will not stay open",
        "the lens cap is shattered",
        "there is significant water ingress despite IP67 rating",
        "the firmware appears corrupted and the device is stuck in a boot loop",
    ],
    "clothing": [
        "the zip broke on the first use",
        "the seam along the left shoulder has completely come apart",
        "two buttons are missing and a third is cracked",
        "the sole has delaminated from the upper after one wear",
        "there is a large snag in the fabric that was not caused by me",
        "the colour has run and the garment has shrunk two sizes after one cold wash",
        "the stitching along the hem is coming undone",
    ],
    "furniture": [
        "one leg arrived snapped in two",
        "the drawer runners are misaligned and the drawers will not close",
        "the hinge on the door is bent and the door hangs at an angle",
        "a main panel arrived with a deep gouge along its length",
        "the pre-drilled holes are misaligned making assembly impossible",
        "the glass top arrived with a hairline crack across the centre",
        "the cushion foam is visibly compressed and misshapen",
    ],
    "toys": [
        "a wheel snapped off on the first use",
        "the battery compartment cover is cracked and the batteries fall out",
        "the arm joint is loose and the arm falls off",
        "the motor does not work — the item will not move",
        "multiple pieces are missing from the box",
        "the LED display is blank despite new batteries",
    ],
    "books": [
        "multiple pages are missing from the middle of the book",
        "the spine is broken and pages are falling out",
        "the cover is water damaged and wrinkled throughout",
    ],
    "health": [
        "the seal was broken on delivery",
        "the lid does not close properly and the powder has spilled",
        "the product is past its expiry date",
    ],
    "general": [
        "the item arrived visibly damaged",
        "the product does not match the description",
        "the item is defective and does not work as advertised",
    ],
    "automotive": ["the fitting is incorrect for the stated vehicle", "the seal is damaged"],
    "crafts": ["the clasp is broken", "the mechanism is faulty"],
    "food": ["the seal was broken", "the product was past its expiry date"],
}

_COURIERS = ["Royal Mail", "DPD", "Evri", "DHL", "UPS", "FedEx", "Yodel", "Amazon Logistics"]

def _make_customers(n: int = 100) -> list[dict]:
    customers = []
    used_emails: set = set()
    for i in range(n):
        first = random.choice(UK_FIRST_NAMES)
        last = random.choice(UK_LAST_NAMES)
        email_base = f"{first.lower()}.{last.lower()}{random.randint(1, 99)}"
        domain = random.choice(["gmail.com", "hotmail.co.uk", "yahoo.co.uk", "outlook.com", "icloud.com"])
        email = f"{email_base}@{domain}"
        while email in used_emails:
            email = f"{email_base}{random.randint(1,9)}@{domain}"
        used_emails.add(email)
        customers.append({
            "id": f"cust_{i+1:04d}",
            "name": f"{first} {last}",
            "email": email,
            "phone": f"07{random.randint(100000000, 999999999)}",
            "city": random.choice(UK_CITIES),
            "dispute_count": random.randint(0, 4),
            "fraud_risk_score": round(random.choices(
                [random.uniform(0.0, 0.1), random.uniform(0.1, 0.3), random.uniform(0.3, 0.7)],
                weights=[0.75, 0.20, 0.05]
            )[0], 3),
        })
    return customers

def _random_date_between(start_days_back: int, end_days_back: int) -> datetime:
    days = random.randint(end_days_back, start_days_back)
    return datetime.utcnow() - timedelta(days=days)

def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d %B %Y").lstrip("0") if hasattr(dt, "strftime") else str(dt)

def _make_dispute_description(category: str, product: dict, order: dict, _customer: dict, seller: dict) -> str:
    cat = product["category"]
    part = random.choice(_PARTS_BY_CATEGORY.get(cat, _PARTS_BY_CATEGORY["general"]))
    fault = random.choice(_FAULTS_BY_CATEGORY.get(cat, _FAULTS_BY_CATEGORY["general"]))
    courier = random.choice(_COURIERS)
    city = random.choice(UK_CITIES)

    purchase_dt = datetime.fromisoformat(order["date"])
    delivery_dt = purchase_dt + timedelta(days=random.randint(1, 5))
    expected_dt = purchase_dt + timedelta(days=random.randint(2, 7))
    last_scan_dt = purchase_dt + timedelta(days=random.randint(1, 3))
    days_overdue = random.randint(5, 45)
    today_dt = expected_dt + timedelta(days=days_overdue)

    ctx = {
        "product": product["name"],
        "order_id": order["id"],
        "price": f"{product['price_gbp']:.2f}",
        "purchase_date": _fmt_date(purchase_dt),
        "delivery_date": _fmt_date(delivery_dt),
        "expected_delivery": _fmt_date(expected_dt),
        "last_scan_date": _fmt_date(last_scan_dt),
        "days_overdue": days_overdue,
        "today": _fmt_date(today_dt),
        "city": city,
        "courier": courier,
        "seller_name": seller["name"],
        "part": part,
        "fault": fault,
        "discounted_price": f"{product['price_gbp'] * 0.85:.2f}",
        "overcharge_amount": f"{product['price_gbp'] * 0.15:.2f}",
    }

    templates_map = {
        "damage": DAMAGE_TEMPLATES,
        "non_delivery": NON_DELIVERY_TEMPLATES,
        "fraud": FRAUD_TEMPLATES,
        "other": OTHER_TEMPLATES,
    }
    template = random.choice(templates_map.get(category, OTHER_TEMPLATES))
    return template.format(**ctx)

def _make_disputes(
    customers: list[dict],
    sellers: list[dict],
    products: list[dict],
    n: int = 500,
) -> list[dict]:
    category_weights = [0.30, 0.35, 0.15, 0.20]
    categories = ["fraud", "damage", "non_delivery", "other"]
    channels = ["web", "mobile", "phone", "email"]
    resolutions_by_cat = {
        "fraud":        ["refund", "refund", "refund", "reject", "escalate"],
        "damage":       ["refund", "replace", "replace", "refund", "reject"],
        "non_delivery": ["refund", "refund", "replace", "escalate", "refund"],
        "other":        ["refund", "replace", "reject", "escalate", "refund"],
    }

    disputes = []
    for i in range(n):
        customer = random.choice(customers)
        product = random.choice(products)
        seller = next(s for s in sellers if s["id"] == product["seller_id"])
        category = random.choices(categories, weights=category_weights)[0]
        purchase_dt = _random_date_between(400, 7)
        order_id = f"ord_{uuid.uuid4().hex[:8]}"
        dispute_id = f"disp_{uuid.uuid4().hex[:10]}"

        order = {
            "id": order_id,
            "date": purchase_dt.isoformat(),
            "total_value": product["price_gbp"],
            "status": random.choice(["delivered", "in_transit", "cancelled", "delivered", "delivered"]),
            "channel": random.choice(channels),
        }

        description = _make_dispute_description(category, product, order, customer, seller)
        resolution = random.choice(resolutions_by_cat[category])
        confidence = round(random.gauss(0.78, 0.12), 3)
        confidence = max(0.45, min(0.99, confidence))

        evidence = []
        if random.random() < 0.15:
            evidence.append({
                "id": f"ev_{uuid.uuid4().hex[:8]}",
                "type": random.choice(["photo", "photo", "receipt", "screenshot"]),
                "damage_score": round(random.uniform(0.4, 0.95), 3),
                "validity_score": round(random.uniform(0.6, 0.99), 3),
                "description": f"Evidence for {category} dispute — {product['name']}",
            })

        disputes.append({
            "dispute": {
                "id": dispute_id,
                "category": category,
                "channel": random.choice(channels),
                "status": "resolved",
                "resolution": resolution,
                "confidence": confidence,
                "description": description,
                "created_at": purchase_dt.isoformat(),
            },
            "order": order,
            "customer_id": customer["id"],
            "product_sku": product["sku"],
            "seller_id": seller["id"],
            "evidence": evidence,
        })

    return disputes

def _make_seller_policies() -> list[dict]:
    policies = []
    for seller in SELLERS:
        return_days = random.choice([14, 28, 30])
        policies.append({
            "id": f"pol_{seller['id']}",
            "seller_id": seller["id"],
            "source": f"seller_policy_{seller['id']}",
            "clause": f"{seller['name']} Returns Policy",
            "text": (
                f"{seller['name']} accepts returns within {return_days} days of delivery for any reason. "
                f"Items must be returned in their original condition and packaging. "
                f"Refunds are processed within 5 business days of receiving the returned item. "
                f"For items that arrive damaged or defective, we offer free returns and either a "
                f"full replacement or refund at the customer's choice. "
                f"Proof of purchase (order confirmation) must be provided. "
                f"Return shipping is free for damaged/defective items and costs £3.99 for change-of-mind returns. "
                f"We comply fully with the Consumer Rights Act 2015 and the Consumer Contracts Regulations 2013."
            ),
            "version_date": "2024-01-01T00:00:00",
        })
    return policies

def main():
    print("Generating customers...")
    customers = _make_customers(100)
    _save("customers.json", customers)
    print(f"  {len(customers)} customers")

    print("Saving sellers...")
    _save("sellers.json", SELLERS)
    print(f"  {len(SELLERS)} sellers")

    print("Saving products...")
    _save("products.json", PRODUCTS)
    print(f"  {len(PRODUCTS)} products")

    print("Generating disputes...")
    disputes = _make_disputes(customers, SELLERS, PRODUCTS, n=500)
    _save("disputes.json", disputes)
    print(f"  {len(disputes)} disputes")

    print("Generating seller policies...")
    policies = _make_seller_policies()
    _save("policies.json", policies)
    print(f"  {len(policies)} seller policies")

    print(f"\nAll data written to {DATA_DIR}/")
    print("Run: python scripts/load_to_neo4j.py   to embed and load into Neo4j")

def _save(filename: str, data):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Saved {path}")

if __name__ == "__main__":
    main()
