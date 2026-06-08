"""
========================================================
  E-Commerce Price Intelligence Scraper
  Author  : Your Name (Upwork)
  Version : 1.0.0
  Desc    : Scrapes product prices from demo/sample
            e-commerce sites and saves to CSV.
            Swap SITES config to use real competitors.
========================================================
"""

import csv
import random
import time
import logging
from datetime import datetime
from dataclasses import dataclass, fields
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── Logging Setup ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Output CSV ───────────────────────────────────────────
OUTPUT_CSV = "data/prices.csv"

# ── Demo Sites Config ────────────────────────────────────
# These are public demo/sandbox e-commerce sites.
# Replace with your real competitor URLs.
SITES = [
    {
        "name": "Books To Scrape",
        "base_url": "https://books.toscrape.com/catalogue/",
        "list_url": "https://books.toscrape.com/catalogue/page-{page}.html",
        "pages": 3,
        "parser": "parse_books_to_scrape",
    },
]

# ── User-Agent Pool ───────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
]


# ── Data Model ────────────────────────────────────────────
@dataclass
class Product:
    timestamp:    str
    site:         str
    category:     str
    product_name: str
    price_gbp:    float
    rating:       str
    availability: str
    url:          str
    price_change: Optional[float] = None   # filled by comparator


# ── HTTP Helper ───────────────────────────────────────────
def fetch(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    log.error(f"All retries exhausted for {url}")
    return None


# ── Site Parsers ──────────────────────────────────────────
def parse_books_to_scrape(site_cfg: dict) -> list[Product]:
    """Parse books.toscrape.com — a public scraping sandbox."""
    products = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for page in range(1, site_cfg["pages"] + 1):
        url = site_cfg["list_url"].format(page=page)
        log.info(f"  Scraping {site_cfg['name']} — page {page}")
        soup = fetch(url)
        if not soup:
            continue

        for article in soup.select("article.product_pod"):
            try:
                name_tag = article.select_one("h3 a")
                name  = name_tag["title"]
                href  = site_cfg["base_url"] + name_tag["href"].replace("../", "")
                price = float(article.select_one("p.price_color").text.strip().replace("£", "").replace("Â", ""))
                rating_map = {"One": "1★", "Two": "2★", "Three": "3★", "Four": "4★", "Five": "5★"}
                rating_cls = article.select_one("p.star-rating")["class"][1]
                rating     = rating_map.get(rating_cls, "N/A")
                avail      = article.select_one("p.availability").text.strip()

                # Derive a rough category from the breadcrumb on detail page (cached lightly)
                category = "Books"

                products.append(Product(
                    timestamp    = now,
                    site         = site_cfg["name"],
                    category     = category,
                    product_name = name,
                    price_gbp    = price,
                    rating       = rating,
                    availability = avail,
                    url          = href,
                ))
            except Exception as e:
                log.warning(f"  Parse error on product: {e}")

        # Polite delay between pages
        time.sleep(random.uniform(1.0, 2.5))

    return products


# ── CSV Writer ────────────────────────────────────────────
def save_to_csv(products: list[Product], path: str):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.isfile(path)
    col_names = [f.name for f in fields(Product)]

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        if not file_exists:
            writer.writeheader()
        for p in products:
            writer.writerow({f.name: getattr(p, f.name) for f in fields(p)})

    log.info(f"Saved {len(products)} records → {path}")


# ── Price Change Detector ─────────────────────────────────
def detect_price_changes(new_products: list[Product], csv_path: str) -> list[Product]:
    """Compare new prices against last recorded prices."""
    import os
    if not os.path.isfile(csv_path):
        return new_products

    last_prices: dict[str, float] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = f"{row['site']}|{row['product_name']}"
            last_prices[key] = float(row["price_gbp"])

    alerts = []
    for p in new_products:
        key = f"{p.site}|{p.product_name}"
        if key in last_prices:
            diff = round(p.price_gbp - last_prices[key], 2)
            p.price_change = diff
            if diff != 0:
                direction = "▲ UP" if diff > 0 else "▼ DOWN"
                log.info(f"  PRICE CHANGE {direction} £{abs(diff):.2f}  →  {p.product_name[:50]}")
                alerts.append(p)
    return alerts


# ── Main Orchestrator ─────────────────────────────────────
def run_scraper():
    log.info("=" * 55)
    log.info("  Price Intelligence Scraper — Starting")
    log.info("=" * 55)

    parser_map = {
        "parse_books_to_scrape": parse_books_to_scrape,
    }

    all_products: list[Product] = []

    for site in SITES:
        log.info(f"► Scraping site: {site['name']}")
        parser_fn = parser_map.get(site["parser"])
        if not parser_fn:
            log.error(f"  No parser found for '{site['parser']}' — skipping")
            continue
        products = parser_fn(site)
        log.info(f"  ✓ Collected {len(products)} products from {site['name']}")
        all_products.extend(products)

    if not all_products:
        log.warning("No products scraped. Check your network or site configs.")
        return

    # Detect price changes before saving
    alerts = detect_price_changes(all_products, OUTPUT_CSV)
    if alerts:
        log.info(f"\n⚡ {len(alerts)} price change(s) detected this run!")
    else:
        log.info("\n✓ No price changes detected.")

    save_to_csv(all_products, OUTPUT_CSV)

    log.info("=" * 55)
    log.info(f"  Done. Total records: {len(all_products)}")
    log.info("=" * 55)


if __name__ == "__main__":
    run_scraper()
