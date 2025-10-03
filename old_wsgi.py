import os
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler

# --- Load .env ---
load_dotenv()

# --- Handlers ---
def start(update, context):
    update.message.reply_text("✅ Bot is running!")

def help_command(update, context):
    update.message.reply_text("Here are the commands:\n/start - start bot\n/help - show help")

# --- Main ---
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("❌ TELEGRAM_TOKEN not found. Please set it in your .env file.")

    # ✅ v13 style (token is positional arg)
    updater = Updater(token)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))

    # Start bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
