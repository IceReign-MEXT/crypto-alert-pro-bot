import os
import logging
import requests
import sqlite3
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    CallbackContext,
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# --- Load environment variables ---
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
PAYMENT_GATEWAY_API_KEY = os.getenv("PAYMENT_GATEWAY_API_KEY") # Your payment gateway API key
PAYMENT_GATEWAY_SECRET = os.getenv("PAYMENT_GATEWAY_SECRET") # Your payment gateway webhook secret

DATABASE_NAME = "bot.db"

# --- Subscription Plans ---
SUBSCRIPTION_PLANS = {
    "monthly": {"name": "1 Month", "price_usd": 15.00, "duration_minutes": 43200},
}

# --- Logging ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Database ---
def initialize_db():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS premium_users (
                user_id INTEGER PRIMARY KEY,
                is_premium BOOLEAN NOT NULL DEFAULT 0,
                premium_until INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                user_id INTEGER,
                crypto TEXT,
                target_price REAL,
                direction TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        conn.commit()

def set_premium_status(user_id: int, is_premium: bool, premium_until: int = None):
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO premium_users (user_id, is_premium, premium_until)
            VALUES (?, ?, ?)
        """, (user_id, is_premium, premium_until))
        conn.commit()

def get_premium_status(user_id: int):
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.execute("SELECT is_premium, premium_until FROM premium_users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            is_premium, premium_until_ts = result
            if is_premium and premium_until_ts and premium_until_ts < time.time():
                set_premium_status(user_id, False)
                return False, None
            return bool(is_premium), premium_until_ts
        return False, None

def add_alert(user_id: int, crypto: str, target: float, direction: str):
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("INSERT INTO alerts (user_id, crypto, target_price, direction) VALUES (?, ?, ?, ?)", (user_id, crypto, target, direction))
        conn.commit()

def get_active_alerts():
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.execute("SELECT user_id, crypto, target_price, direction FROM alerts WHERE is_active = 1")
        return cursor.fetchall()

def deactivate_alert(user_id: int, crypto: str, target_price: float):
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute("UPDATE alerts SET is_active = 0 WHERE user_id = ? AND crypto = ? AND target_price = ?", (user_id, crypto, target_price))
        conn.commit()

# --- Bot Commands ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = "Welcome! I am a powerful crypto bot. 🚀 Use /help to see all available commands."
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "Commands:\n\n"
        "/price <crypto> - Get live price\n"
        "/premium - Get premium options (Automated alerts)\n"
        "/setalert <crypto> <price> <up/down> - Set premium price alert\n"
        "/status - Check premium status\n"
    )
    await update.message.reply_text(message)

async def get_crypto_price(ticker: str):
    try:
        params = {"ids": ticker, "vs_currencies": "usd"}
        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get(ticker) and data[ticker].get('usd'):
            return data[ticker]['usd']
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching price for {ticker}: {e}")
        return None

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /price <cryptocurrency_name> (e.g., /price bitcoin)")
        return
    ticker = context.args[0].lower()
    price = await get_crypto_price(ticker)
    if price is not None:
        await update.message.reply_text(f"The current price of {ticker.capitalize()} is ${price}")
    else:
        await update.message.reply_text(f"Could not find price for '{ticker}'.")

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = []
    for tier, plan in SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(f"{plan['name']} (${plan['price_usd']})", callback_data=f"subscribe_{tier}")
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Unlock automated price alerts! Choose a plan below to proceed with payment.", reply_markup=reply_markup)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data.startswith("subscribe_"):
        tier = query.data.split('_')[1]
        plan = SUBSCRIPTION_PLANS.get(tier)
        if not plan:
            await query.message.reply_text("Invalid subscription plan selected.")
            return

        # --- Automated Payment Gateway Logic using Coinbase Commerce (PLACEHOLDER) ---
        api_key = PAYMENT_GATEWAY_API_KEY
        if not api_key:
            await query.message.reply_text("Payment gateway not configured. Please contact the administrator.")
            return

        headers = {
            "Content-Type": "application/json",
            "X-CC-Api-Key": api_key,
        }
        body = {
            "name": f"{plan['name']} Subscription",
            "description": "Subscription for automated price alerts.",
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": plan['price_usd'],
                "currency": "USD"
            },
            "redirect_url": "https://telegram.me/<your_bot_username>", # Replace with your bot's username
            "metadata": {
                "user_id": query.from_user.id,
                "plan_tier": tier,
            }
        }
        try:
            response = requests.post("https://api.commerce.coinbase.com/charges", json=body, headers=headers)
            response.raise_for_status()
            payment_link = response.json()['data']['hosted_url']
            message = (
                f"**{plan['name']} Subscription**\n\n"
                f"**Price:** `${plan['price_usd']}`\n\n"
                f"Click the link below to pay and automatically activate your premium access!\n"
            )
            keyboard = [[InlineKeyboardButton("Pay Now", url=payment_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        except requests.exceptions.RequestException as e:
            logging.error(f"Coinbase Commerce API Error: {e}")
            await query.message.reply_text("There was an error generating the payment link. Please try again later.")

async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_premium, _ = get_premium_status(user_id)
    if not is_premium:
        await update.message.reply_text("This feature is for premium users only. Use /premium to get access.")
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /setalert <crypto> <price> <up/down>")
        return
    crypto = context.args[0].lower()
    try:
        price = float(context.args[1])
        direction = context.args[2].lower()
        if direction not in ["up", "down"]:
            raise ValueError
        add_alert(user_id, crypto, price, direction)
        await update.message.reply_text(f"Alert set for {crypto.upper()} at ${price} ({direction}).")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid price or direction. Please use a number for the price and 'up' or 'down' for the direction.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_premium, premium_until_ts = get_premium_status(user_id)
    if is_premium:
        until_datetime = datetime.fromtimestamp(premium_until_ts)
        message = f"You are currently a **Premium User**! 🎉\nYour subscription is valid until: `{until_datetime.strftime('%Y-%m-%d %H:%M:%S')}`."
    else:
        message = "You are a standard user.\nUnlock premium features with a subscription. Use /premium to see options."
    await update.message.reply_text(message, parse_mode='Markdown')

# --- Background Task for Price Alerts ---
async def check_alerts(context: CallbackContext):
    alerts = get_active_alerts()
    if not alerts:
        return

    cryptos = list(set([alert[1] for alert in alerts]))
    if not cryptos:
        return

    params = {"ids": ",".join(cryptos), "vs_currencies": "usd"}
    try:
        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching prices for alerts: {e}")
        return

    for user_id, crypto, target_price, direction in alerts:
        current_price = data.get(crypto, {}).get('usd')
        if current_price is None:
            continue

        alert_triggered = False
        if direction == "up" and current_price >= target_price:
            alert_triggered = True
        elif direction == "down" and current_price <= target_price:
            alert_triggered = True

        if alert_triggered:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🔔 **ALERT!** {crypto.upper()} has hit your target price of ${target_price}. The current price is ${current_price}.",
                    parse_mode='Markdown'
                )
                deactivate_alert(user_id, crypto, target_price)
            except Exception as e:
                logging.error(f"Error sending alert to user {user_id}: {e}")


# --- Webhook endpoint for automated payment gateway ---
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def handle_payment_webhook():
    # Placeholder for webhook verification logic
    # In a real-world scenario, you would verify the signature of the webhook
    # using the payment gateway's secret to ensure it's not a fraudulent request.
    payload = request.json
    event_type = payload.get('event', {}).get('type')

    if event_type == 'charge:confirmed':
        user_id = payload.get('event', {}).get('data', {}).get('metadata', {}).get('user_id')
        plan_tier = payload.get('event', {}).get('data', {}).get('metadata', {}).get('plan_tier')
        if user_id and plan_tier:
            plan = SUBSCRIPTION_PLANS.get(plan_tier)
            if plan:
                duration_minutes = plan['duration_minutes']
                premium_until = int(time.time()) + duration_minutes * 60
                set_premium_status(user_id, True, premium_until)

                # Send confirmation message to the user
                application = Application.builder().token(TELEGRAM_TOKEN).build()
                async with application:
                    try:
                        await application.bot.send_message(
                            chat_id=user_id,
                            text="✅ Your premium subscription has been activated! Enjoy your new features.",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logging.error(f"Error sending confirmation to user {user_id}: {e}")

                return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'ignored'}), 200

# --- Main Bot Function ---
def main() -> None:
    initialize_db()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_alerts, 'interval', minutes=5, args=(application,))
    scheduler.start()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("setalert", set_alert_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Start the Flask app for webhooks
    app.run(host='0.0.0.0', port=10000)


