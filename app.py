import os
import requests
import logging
from dotenv import load_dotenv

from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler

# Load environment variables from .env file
load_dotenv()

# Set up logging for better debugging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# Load bot token and webhook URL from environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Render automatically provides a URL in production
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not TOKEN or not RENDER_EXTERNAL_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN and RENDER_EXTERNAL_URL must be set")

WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}/{TOKEN}"

# Initialize the python-telegram-bot Application
bot_app = Application.builder().token(TOKEN).build()

# Define a command handler for the /start command
async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I am running on Render."
    )

# Add the command handler to the application
bot_app.add_handler(CommandHandler("start", start))

# Flask route to handle webhook updates from Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    # Receive update from Telegram
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot_app.bot)
    
    # Process the update
    await bot_app.process_update(update)
    
    return "ok"

# Route for setting the webhook
@app.route("/set_webhook")
def set_webhook():
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
        response.raise_for_status()
        return f"Webhook set successfully: {response.json()}"
    except requests.exceptions.RequestException as e:
        return f"Error setting webhook: {e}"

# Simple root route for health checks
@app.route("/")
def index():
    return "Bot is running. Visit /set_webhook to configure it."

# This is for local testing only. In production, Gunicorn starts the server.
if __name__ == "__main__":
    app.run(port=os.environ.get("PORT", 5000))
