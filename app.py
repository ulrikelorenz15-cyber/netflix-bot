# ================================
# 🎬 NETFLIX SYSTEM (ULTRA STABLE)
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None

DATA_FILE = "data.json"

# ================================
# SAFETY START
# ================================

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN fehlt!")
else:
    print("✅ BOT TOKEN OK")

# ================================
# DATA SAFE
# ================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print("LOAD ERROR:", e)
    return {"movies": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("SAVE ERROR:", e)

def get_id(data):
    try:
        return str(len(data["movies"]) + 1).zfill(4)
    except:
        return "0001"

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
# ULTRA PARSER
# ================================

def extract(text):
    try:
        if not text:
            return None

        title_match = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)

        if not title_match:
            print("❌ NO TITLE MATCH")
            return None

        title = title_match.group(1).strip()
        year = title_match.group(2)

        return {
            "title": title,
            "year": year,
            "rating": safe(r"⭐\s*([0-9.]+)", text),
            "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
            "genre": re.findall(r"#(\w+)", text)[:2] or ["Unknown"],
            "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
        }

    except Exception as e:
        print("PARSER ERROR:", e)
        return None

# ================================
# POSTER SAFE
# ================================

def get_poster(title):
    try:
        return f"https://image.pollinations.ai/prompt/{title}+movie+poster"
    except:
        return "https://dummyimage.com/600x900/000/fff&text=Movie"

# ================================
# API
# ================================

@app.route("/")
def home():
    return "🔥 ULTRA STABLE NETFLIX SYSTEM RUNNING"

@app.route("/api/movies")
def movies():
    try:
        return jsonify(load_data()["movies"])
    except Exception as e:
        print("API ERROR:", e)
        return jsonify([])

# ================================
# TELEGRAM WEBHOOK (SAFE)
# ================================

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        print("UPDATE:", update)

        if not update:
            return "ok"

        if "message" not in update:
            return "ok"

        msg = update["message"]
        chat_id = msg["chat"]["id"]

        # ====================
        # VIDEO HANDLER
        # ====================

        if "video" in msg or "document" in msg:
            try:
                data = load_data()
                caption = msg.get("caption", "")

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

                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"✅ Gespeichert: {info['title']}"
                })

            except Exception as e:
                print("VIDEO ERROR:", e)

        return "ok"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "ok"

# ================================
# START (RENDER SAFE)
# ================================

if __name__ == "__main__":
    try:
        print("🔥 ULTRA STABLE START")

        if TOKEN and os.getenv("WEBHOOK_URL"):
            try:
                webhook_url = f"{os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}"
                print("SET WEBHOOK:", webhook_url)

                requests.get(f"{URL}/setWebhook?url={webhook_url}")
            except Exception as e:
                print("WEBHOOK SET ERROR:", e)

        port = int(os.environ.get("PORT", 10000))
        print("PORT:", port)

        app.run(host="0.0.0.0", port=port, debug=False)

    except Exception as e:
        print("FATAL ERROR:", e)