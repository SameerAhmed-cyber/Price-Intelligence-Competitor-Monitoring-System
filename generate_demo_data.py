"""Generates realistic demo price data for the dashboard."""
import csv, random, os
from datetime import datetime, timedelta

os.makedirs("data", exist_ok=True)

SITES = ["TechMart", "GadgetHub", "ShopZone", "PriceKing", "MegaStore"]
CATEGORIES = ["Laptops", "Smartphones", "Headphones", "Tablets", "Cameras", "Accessories"]
PRODUCTS = {
    "Laptops":      ["Dell XPS 15","MacBook Pro 14","HP Spectre x360","Lenovo ThinkPad X1","Asus ZenBook 14","Acer Swift 5","MSI Prestige 15"],
    "Smartphones":  ["iPhone 15 Pro","Samsung Galaxy S24","Google Pixel 8","OnePlus 12","Xiaomi 14 Pro","Sony Xperia 1 VI","Nothing Phone 2"],
    "Headphones":   ["Sony WH-1000XM5","Bose QC45","Apple AirPods Max","Sennheiser HD 560S","JBL Tune 770NC","Jabra Evolve2 55"],
    "Tablets":      ["iPad Pro 12.9","Samsung Tab S9","Microsoft Surface Pro 9","Lenovo Tab P12","Amazon Fire HD 10"],
    "Cameras":      ["Sony A7 IV","Canon EOS R6","Nikon Z6 III","Fujifilm X-T5","OM System OM-5"],
    "Accessories":  ["Anker 65W Charger","Logitech MX Master 3","Samsung T7 SSD","Belkin MagSafe","Spigen Case"],
}
BASE_PRICES = {
    "Laptops":700,"Smartphones":500,"Headphones":150,"Tablets":400,"Cameras":1200,"Accessories":40
}

rows = []
now = datetime.now()
for day_offset in range(14):  # 14 days of data
    ts = (now - timedelta(days=13 - day_offset)).strftime("%Y-%m-%d %H:%M:%S")
    for cat, prods in PRODUCTS.items():
        for prod in prods:
            base = BASE_PRICES[cat]
            for site in SITES:
                # Each site has a slight base multiplier
                site_mult = {"TechMart":1.0,"GadgetHub":0.97,"ShopZone":1.03,"PriceKing":0.95,"MegaStore":1.01}[site]
                # Add daily drift
                drift = random.uniform(-0.05, 0.05) * day_offset
                price = round(base * site_mult * (1 + drift) + random.uniform(-5,5), 2)
                price = max(price, base * 0.7)
                prev_price = None
                if day_offset > 0:
                    prev_price = round(price + random.choice([-1,0,0,1]) * random.uniform(0,15), 2)
                change = round(price - prev_price, 2) if prev_price else None
                rows.append({
                    "timestamp": ts,
                    "site": site,
                    "category": cat,
                    "product_name": prod,
                    "price_gbp": price,
                    "rating": random.choice(["3★","4★","4★","5★","5★"]),
                    "availability": random.choice(["In stock","In stock","In stock","Low stock","Out of stock"]),
                    "url": f"https://{site.lower()}.demo/{prod.replace(' ','-').lower()}",
                    "price_change": change,
                })

with open("data/prices.csv","w",newline="",encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> data/prices.csv")
