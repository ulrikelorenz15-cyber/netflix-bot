import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# PARSER
# ================================

def extract(text):
    try:
        return {
            "title": re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text).group(1),
            "year": re.search(r"\((\d{4})\)", text).group(1),
            "rating": re.search(r"⭐\s*([0-9.]+)", text).group(1),
            "runtime": re.search(r"⏱\s*([0-9]+\s*Min)", text).group(1),
            "genre": re.findall(r"#(\w+)", text)[:2],
            "story": re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S).group(1).strip()
        }
    except:
        return None

# ================================
# ROUTES
# ================================

@app.route("/")
def home():
    return "🔥 Netflix System Running"

@app.route("/api/movies")
def movies():
    return jsonify(load_data()["movies"])

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    data = load_data()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg:
            info = extract(msg.get("caption", ""))

            if not info:
                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Fehler beim Erkennen"
                })
                return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg["video"]["file_id"],
                "views": 0,
                "timestamp": time.time()
            }

            data["movies"].append(entry)
            save_data(data)

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ {info['title']} gespeichert"
            })

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 DEPLOY READY START")

    # Webhook setzen
    if os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)