import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

# Load from .env
CRYPTOMUS_PAYMENT_KEY = os.getenv("CRYPTOMUS_PAYMENT_KEY")
CRYPTOMUS_WEBHOOK_URL = os.getenv("CRYPTOMUS_WEBHOOK_URL")

# Subscription Prices
PRICES = {
    "monthly": 15,   # USD
    "yearly": 100    # USD
}

# ---------------------------
# /subscribe command
# ---------------------------
def subscribe(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💳 $15 / Monthly", callback_data="sub_monthly")],
        [InlineKeyboardButton("💎 $100 / Yearly", callback_data="sub_yearly")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose your subscription plan:", reply_markup=reply_markup)

# ---------------------------
# Handle button click
# ---------------------------
def handle_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "sub_monthly":
        amount = PRICES["monthly"]
        plan = "Monthly"
    elif query.data == "sub_yearly":
        amount = PRICES["yearly"]
        plan = "Yearly"
    else:
        query.edit_message_text("❌ Invalid selection")
        return

    # Create Cryptomus invoice
    payload = {
        "amount": str(amount),
        "currency": "USD",
        "order_id": f"{query.from_user.id}-{plan.lower()}",
        "url_callback": CRYPTOMUS_WEBHOOK_URL,
        "description": f"{plan} Subscription for {query.from_user.first_name}",
    }

    headers = {
        "merchant": CRYPTOMUS_PAYMENT_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.cryptomus.com/v1/payment",
                                 json=payload, headers=headers)
        data = response.json()
        if "result" in data:
            payment_url = data["result"]["url"]
            query.edit_message_text(
                text=f"✅ Please complete your {plan} payment:\n{payment_url}"
            )
        else:
            query.edit_message_text("⚠️ Payment error. Try again later.")

    except Exception as e:
        query.edit_message_text(f"❌ Error: {str(e)}")
