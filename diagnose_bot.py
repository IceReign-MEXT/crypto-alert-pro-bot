import os
import sys
import importlib.util
import requests

REQUIRED_ENV_VARS = [
    "TELEGRAM_TOKEN",
    "PAYMENT_PROVIDER",
]

REQUIRED_PACKAGES = {
    "python-telegram-bot": "20.7",
    "requests": None,
    "flask": None,
    "apscheduler": None,
}

def check_env_vars():
    print("\n🔍 Checking Environment Variables...")
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
            print(f"❌ Missing: {var}")
        else:
            print(f"✅ {var} = {os.getenv(var)[:6]}... (loaded)")
    return missing

def check_packages():
    print("\n🔍 Checking Python Packages...")
    missing = []
    for pkg, required_version in REQUIRED_PACKAGES.items():
        spec = importlib.util.find_spec(pkg.replace("-", "_"))
        if spec is None:
            missing.append(pkg)
            print(f"❌ Missing package: {pkg}")
        else:
            try:
                module = __import__(pkg.replace("-", "_"))
                version = getattr(module, "__version__", "unknown")
                if required_version and version != required_version:
                    print(f"⚠️ {pkg} version {version} (expected {required_version})")
                else:
                    print(f"✅ {pkg} {version}")
            except Exception as e:
                print(f"⚠️ Could not check {pkg}: {e}")
    return missing

def check_telegram_token():
    print("\n🔍 Validating Telegram Token...")
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ TELEGRAM_TOKEN not set")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        resp = requests.get(url, timeout=5).json()
        if resp.get("ok"):
            print(f"✅ Token valid! Bot: {resp['result']['username']}")
            return True
        else:
            print(f"❌ Invalid token: {resp}")
            return False
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return False

if __name__ == "__main__":
    print("=== 🤖 BOT DIAGNOSTICS ===")
    env_missing = check_env_vars()
    pkg_missing = check_packages()
    token_ok = check_telegram_token()

    print("\n=== SUMMARY ===")
    if not env_missing and not pkg_missing and token_ok:
        print("🎉 All checks passed. Bot environment is READY.")
    else:
        print("⚠️ Issues detected. Please fix the above before running the bot.")
        sys.exit(1)
