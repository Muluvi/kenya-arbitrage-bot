import os
import requests
import telebot
from scraper_cron import (
    get_ebay_token,
    search_ebay_active,
    estimate_resale_usd,
    calculate_profit,
    get_usd_kes_rate
)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
EBAY_CLIENT_ID = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
        "🇰🇪 *Kenya Arbitrage Bot*\n\n"
        "Send me an item title and price (in KSh) like:\n"
        "`Wooden giraffe carving 1200`\n\n"
        "I'll estimate the eBay resale value and profit.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_query(message):
    text = message.text.strip()
    if not text:
        return
    # Try to split into title and price
    parts = text.rsplit(" ", 1)
    price_kes = None
    title = text
    if len(parts) > 1 and parts[-1].replace(",", "").isdigit():
        try:
            price_kes = float(parts[-1].replace(",", ""))
            title = parts[0]
        except:
            pass
    bot.send_chat_action(message.chat.id, 'typing')
    items = search_ebay_active(title)
    if not items:
        bot.reply_to(message, "❌ No active eBay listings found. Try a broader title.")
        return
    resale = estimate_resale_usd(items)
    if resale is None:
        bot.reply_to(message, "⚠️ Could not determine a reliable price.")
        return
    # Build reply with top comps
    reply = f"*eBay estimate (discounted 15%)*: ${resale:.2f}\n\n"
    reply += "Top active listings:\n"
    for it in items[:3]:
        price = it["price"]["value"]
        url = it["itemWebUrl"]
        title_short = it["title"][:60]
        reply += f"• ${price} – [{title_short}]({url})\n"
    bot.reply_to(message, reply, parse_mode="Markdown", disable_web_page_preview=True)

    if price_kes:
        net, margin, buy_usd = calculate_profit(price_kes, resale, category="general")
        detail = (
            f"💰 *Profit Breakdown*\n"
            f"Buy: KSh {price_kes:,.0f} (${buy_usd:.2f})\n"
            f"eBay sale est: ${resale:.2f}\n"
            f"Net profit: ${net:.2f}\n"
            f"Margin: {margin:.1%}\n\n"
            f"_(includes eBay fees, shipping from Kenya, and Payoneer withdrawal)_"
        )
        bot.send_message(message.chat.id, detail, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot polling...")
    bot.infinity_polling()
