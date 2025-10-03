import os, requests, json
from flask import Flask, request
from dotenv import load_dotenv
from db import add_subscription

load_dotenv()

PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "cryptomus")

app = Flask(__name__)

# ----------------------
# CRYPTOMUS INTEGRATION
# ----------------------
CRYPTOMUS_PAYMENT_KEY = os.getenv("CRYPTOMUS_PAYMENT_KEY")
CRYPTOMUS_WEBHOOK_URL = os.getenv("CRYPTOMUS_WEBHOOK_URL")

CRYPTOMUS_API = "https://api.cryptomus.com/v1/payment"

def create_cryptomus_invoice(amount_usd, order_id, user_id):
    headers = {
        "merchant": CRYPTOMUS_PAYMENT_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "amount": str(amount_usd),
        "currency": "USDT",
        "order_id": order_id,
        "url_callback": CRYPTOMUS_WEBHOOK_URL,
        "user_id": str(user_id)  # pass telegram user id
    }
    r = requests.post(CRYPTOMUS_API, headers=headers, data=json.dumps(data))
    return r.json()

@app.route("/cryptomus/webhook", methods=["POST"])
def cryptomus_webhook():
    payload = request.json
    order_id = payload.get("order_id")
    status = payload.get("status")
    user_id = payload.get("user_id")

    if status == "paid" and user_id:
        add_subscription(int(user_id), days=30)
        print(f"✅ User {user_id} subscribed for 30 days!")

    return {"ok": True}
