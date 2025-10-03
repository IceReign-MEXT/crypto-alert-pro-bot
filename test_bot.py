import os
from telegram import Bot

# --- put your bot token directly for testing ---
TOKEN = "8260238141:AAFbchRRqvnh6PTRKR3n15LrnXxASFbWn-k"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # replace with your own chat id

bot = Bot(token=TOKEN)

try:
    bot.send_message(chat_id=CHAT_ID, text="✅ Bot is alive and working locally!")
    print("Message sent successfully ✅")
except Exception as e:
    print("❌ Error:", e)

