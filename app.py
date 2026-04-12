# ================================
# 🎬 NETFLIX SYSTEM (DEV TOOLKIT MODE)
# ================================

import os
import json
import requests
import re
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None
DATA_FILE = "data.json"

LOGS = []

# ================================
# 🧠 LOGGER (LIVE DEBUG)
# ================================

def log(msg):
    print(msg)
    LOGS.append(str(msg))
    if len(LOGS) > 100:
        LOGS.pop(0)

# ================================
# SAFE START
# ================================

if not TOKEN:
    log("❌ BOT_TOKEN fehlt!")
else:
    log("✅ BOT TOKEN OK")

# ================================
# DATA SAFE
# ================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            return json.load(open(DATA_FILE))
    except Exception as e:
        log(f"LOAD ERROR: {e}")
    return {"movies": []}

def save_data(data):
    try:
        json.dump(data, open(DATA_FILE, "w"))
    except Exception as e:
        log(f"SAVE ERROR: {e}")

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# SAFE REGEX
# ================================

def safe(pattern, text):
    try:
        m = re.search(pattern, text, re.S)
        return m.group(1).strip() if m else "-"
    except:
        return "-"

# ================================
# PARSER
# ================================

def extract(text):
    try:
        t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
        if not t:
            log("❌ NO TITLE MATCH")
            return None

        return {
            "title": t.group(1).strip(),
            "year": t.group(2),
            "rating": safe(r"⭐\s*([0-9.]+)", text),
            "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
            "genre": re.findall(r"#(\w+)", text)[:2] or ["Unknown"],
            "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
        }

    except Exception as e:
        log(f"PARSER ERROR: {e}")
        return None

# ================================
# POSTER
# ================================

def get_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

# ================================
# DEBUG ROUTES
# ================================

@app.route("/")
def home():
    return "🔥 DEV TOOLKIT RUNNING"

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "movies": len(load_data()["movies"])
    })

@app.route("/logs")
def logs():
    return "<br>".join(LOGS)

@app.route("/api/movies")
def movies():
    return jsonify(load_data()["movies"])

# ================================
# TELEGRAM WEBHOOK
# ================================

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        log(f"UPDATE: {update}")

        if not update or "message" not in update:
            return "ok"

        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg or "document" in msg:
            data = load_data()
            caption = msg.get("caption", "")

            log(f"CAPTION: {caption}")

            info = extract(caption)

            if not info:
                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Film nicht erkannt"
                })
                return "ok"

            # DUPLICATE CHECK
            for m in data["movies"]:
                if m["title"].lower() == info["title"].lower():
                    requests.post(f"{URL}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"⚠️ Existiert bereits: {info['title']}"
                    })
                    return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg.get("video", msg.get("document"))["file_id"],
                "views": 0,
                "timestamp": time.time(),
                "poster": get_poster(info["title"])
            }

            data["movies"].append(entry)
            save_data(data)

            log(f"✅ SAVED: {info['title']}")

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ Gespeichert: {info['title']}"
            })

        return "ok"

    except Exception as e:
        log(f"WEBHOOK ERROR: {e}")
        return "ok"

# ================================
# 🔄 KEEP ALIVE
# ================================

def keep_alive():
    while True:
        try:
            url = os.getenv("WEBHOOK_URL")
            if url:
                requests.get(url)
                log("🔄 KEEP ALIVE PING")
        except Exception as e:
            log(f"PING ERROR: {e}")

        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# ================================
# START
# ================================

if __name__ == "__main__":
    log("🔥 DEV TOOLKIT START")

    try:
        if TOKEN and os.getenv("WEBHOOK_URL"):
            webhook_url = f"{os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}"
            log(f"SET WEBHOOK: {webhook_url}")
            requests.get(f"{URL}/setWebhook?url={webhook_url}")
    except Exception as e:
        log(f"WEBHOOK ERROR: {e}")

    port = int(os.environ.get("PORT", 10000))
    log(f"PORT: {port}")

    app.run(host="0.0.0.0", port=port, debug=False)