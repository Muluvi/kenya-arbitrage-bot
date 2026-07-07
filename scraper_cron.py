import os
import sqlite3
import time
import requests
from bs4 import BeautifulSoup
import telebot

# ---------- Configuration from environment ----------
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
EBAY_CLIENT_ID = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY", "demo")

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- SQLite for deduplication ----------
DB_PATH = "listings.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY)")
conn.commit()

# ---------- Exchange rate ----------
def get_usd_kes_rate():
    try:
        resp = requests.get(
            f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD"
        )
        data = resp.json()
        return data["conversion_rates"]["KES"]
    except:
        # Fallback – update periodically if API key fails
        return 155.0

# ---------- eBay Browse API ----------
def get_ebay_token():
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        data="grant_type=client_credentials",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {requests.auth._basic_auth_str(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET)}"
        }
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def search_ebay_active(keywords):
    token = get_ebay_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=0"  # optional
    }
    params = {
        "q": keywords,
        "limit": "10",
        "filter": "conditions:{NEW|USED|UNSPECIFIED}"
    }
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        return []
    return resp.json().get("itemSummaries", [])

def estimate_resale_usd(items, discount=0.85):
    if not items:
        return None
    prices = []
    for it in items:
        try:
            p = float(it["price"]["value"])
            prices.append(p * discount)
        except:
            pass
    if not prices:
        return None
    prices.sort()
    return prices[len(prices) // 2]  # median

# ---------- Shipping cost table (Kenya -> US) ----------
def get_shipping_cost(category="general"):
    # Approximate costs via Kenya Post EMS / DHL for 1-2kg
    if category in ("antiques", "large_art", "furniture"):
        return 40.0
    elif category in ("electronics", "consoles", "laptops"):
        return 25.0
    else:
        return 15.0  # small collectibles, jewelry, stamps

# ---------- Profit calculator ----------
def calculate_profit(local_price_kes, resale_usd, category="general"):
    rate = get_usd_kes_rate()
    buy_usd = local_price_kes / rate
    # eBay US fees (2026, no Store)
    fvf_rate = 0.136
    per_order_fee = 0.40
    payment_withdrawal_fee_rate = 0.02  # Payoneer approx
    shipping = get_shipping_cost(category)
    packaging = 2.0

    total_fees = (resale_usd * fvf_rate) + per_order_fee + (resale_usd * payment_withdrawal_fee_rate)
    net = resale_usd - total_fees - shipping - packaging - buy_usd
    margin = net / buy_usd if buy_usd > 0 else 0.0
    return net, margin, buy_usd

# ---------- Jiji scraper (Antiques category) ----------
def scrape_jiji():
    base_url = "https://jiji.co.ke/antiques?page={}"
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Samsung)"}
    for page in range(1, 4):  # scan first 3 pages
        url = base_url.format(page)
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Jiji listing cards (check selectors; these are valid as of early 2025)
            cards = soup.select("div.b-list-advert__gallery__item")
            if not cards:
                # Fallback selectors if layout changes
                cards = soup.select("div[data-testid='listing-card']")
            for card in cards:
                title_el = card.select_one("div.b-advert-title-inner, h2, a[href]")
                price_el = card.select_one("div.b-list-advert__gallery__item-price, span[class*='price']")
                link_el = card.select_one("a[href]")
                if not title_el or not price_el or not link_el:
                    continue
                title = title_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True).replace("KSh", "").replace(",", "").strip()
                try:
                    price_kes = float(price_text)
                except:
                    continue
                link = link_el.get("href")
                if not link.startswith("http"):
                    link = "https://jiji.co.ke" + link
                item_id = link.split("/")[-1].split("?")[0]  # crude unique ID
                # Dedup
                c.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
                if c.fetchone():
                    continue
                c.execute("INSERT OR IGNORE INTO seen VALUES (?)", (item_id,))
                conn.commit()
                # eBay valuation
                ebay_items = search_ebay_active(title)
                resale = estimate_resale_usd(ebay_items)
                if resale is None:
                    continue
                net, margin, buy_usd = calculate_profit(price_kes, resale, category="antiques")
                if margin >= 0.30:
                    msg = (
                        f"🇰🇪 *Jiji Deal!*\n"
                        f"*{title[:100]}*\n"
                        f"Buy: KSh {price_kes:,.0f} (~${buy_usd:.2f})\n"
                        f"Est. eBay sale: ${resale:.2f}\n"
                        f"Net profit: ${net:.2f}  ({margin:.1%} margin)\n"
                        f"[View Listing]({link})"
                    )
                    bot.send_message(CHAT_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)
                time.sleep(2)  # polite delay
        except Exception as e:
            print(f"Jiji error on page {page}: {e}")
            continue

if __name__ == "__main__":
    scrape_jiji()
