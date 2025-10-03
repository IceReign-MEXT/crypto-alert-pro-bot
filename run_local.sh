#!/bin/bash
set -e

echo "🚀 Setting up local environment for crypto-alert-pro-bot"

# 1. Create and activate venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# 2. Install dependencies
echo "📦 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Export default env vars for local run (replace with your real tokens later)
export TELEGRAM_BOT_TOKEN="TEST_TOKEN"
export PORT=10000

# 4. Run with Gunicorn (production style)
echo "🔥 Starting bot with Gunicorn..."
gunicorn old_wsgi:app -b 0.0.0.0:$PORT --reload --access-logfile - --error-logfile -

# For Flask dev mode instead of Gunicorn, uncomment:
# python old_wsgi.py
