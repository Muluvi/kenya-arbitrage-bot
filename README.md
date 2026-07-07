# kenya-arbitrage-bot
A free Telegram bot that finds arbitrage deals on Kenyan classifieds and estimates resale profit on eBay. 
# 🇰🇪 Kenya → Global Arbitrage Alert Bot

A zero‑cost Telegram bot that finds underpriced items on Kenyan classifieds (Jiji.co.ke, PigiaMe) and estimates resale profit on eBay (US/UK). Built for the Samsung A55 — all alerts and manual lookups happen via Telegram.

**Features:**
- Scrapes Jiji antiques/collectibles every 4 hours (free cloud cron)
- Instantly values any item you send to the bot (manual lookup)
- Profit calc with 2026 eBay fees, shipping from Kenya, real‑time KES/USD rates
- Alerts only when margin ≥ 30%
- All tools are free — no proxies, no paid APIs, no home server

**Architecture:**
- Cron job on Render (scraper + profit engine)
- Telegram bot on Render (persistent polling)
- eBay Browse API (5k calls/day free)
- Exchangerate‑API (1k calls/month free)

## Setup (from your Samsung A55)

1. **Create a Telegram bot**  
   Chat with [@BotFather](https://t.me/BotFather), send `/newbot`, choose a name.  
   Copy the **bot token**.

2. **Get eBay API keys**  
   Go to [developer.ebay.com](https://developer.ebay.com) → Create an app.  
   Copy **App ID (Client ID)** and **Cert ID (Client Secret)**.

3. **Get Exchange Rate API key**  
   Sign up at [exchangerate-api.com](https://www.exchangerate-api.com) (free tier).  
   Copy your API key.

4. **Deploy to Render** (free tier)  
   - Fork/clone this repo to your GitHub.  
   - On [render.com](https://render.com), create a **Cron Job** for `scraper_cron.py` (schedule `0 */4 * * *`).  
   - Create a **Web Service** for `telegram_bot.py` (start command: `python telegram_bot.py`).  
   - Add the environment variables (see `.env.example`) in each service's settings.  

5. **Start using it**  
   - Open your bot on Telegram and send a message like:  
     `Vintage wooden mask 1200` (title + price in KSh).  
   - You'll get an instant eBay valuation and profit estimate.  
   - Automatic alerts from Jiji will start arriving every few hours.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your personal chat ID (get from `getUpdates`) |
| `EBAY_CLIENT_ID` | eBay App ID (Client ID) |
| `EBAY_CLIENT_SECRET` | eBay Cert ID (Client Secret) |
| `EXCHANGE_API_KEY` | API key from exchangerate-api.com |

## Cost
- **Total: $0/month.** All services are on free tiers, eBay API is free, Telegram is free.
- No servers, no proxies, no hidden charges.

## Limitations (honest)
- eBay valuation uses active listing prices × 0.85 (no sold data — Browse API only).  
- Jiji scraping is polite and may have a few hours lag.  
- Facebook Marketplace is manual (paste item into bot).  
- You must verify condition/shipping quotes yourself before buying.
