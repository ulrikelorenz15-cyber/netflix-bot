# ================================
# 🎬 NETFLIX BOT (HARD DEBUG MODE)
# ================================

import os
import json
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

# ================================
# DEBUG SEND (WICHTIG)
# ================================

def debug(chat_id, text):
    print("DEBUG:", text)

    try:
        requests.post(f"{URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"🧠 DEBUG:\n{text}"
        }, timeout=5)
    except Exception as e:
        print("DEBUG ERROR:", e)

# ================================
# SAFE SEND
# ================================

def safe_post(method, payload):
    try:
        print(f"[SEND] {method}")
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except Exception as e:
        print("SEND ERROR:", e)

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

# ================================
# TEST DATA (IMMER DA)
# ================================

def ensure_data():
    data = load_data()

    if not data["movies"]:
        print("👉 Demo Daten geladen")

        data["movies"] = [{
            "id": "0001",
            "title": "Havoc",
            "year": "2025",
            "genre": ["Action", "Thriller"],
            "rating": "7.4",
            "runtime": "125 Min",
            "story": "Test Film läuft korrekt",
            "file_id": None,
            "views": 0
        }]

        save_data(data)

# ================================
# HOME
# ================================

def show_home(chat_id):
    debug(chat_id, "HOME wird geladen")

    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 HOME SCREEN AKTIV"
    })

    if data["movies"]:
        m = data["movies"][0]

        safe_post("sendMessage", {
            "chat_id": chat_id,
            "text": f"🎬 {m['title']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ TEST BUTTON", "callback_data": f"movie_{m['title']}"}
                ]]
            }
        })

# ================================
# CARD
# ================================

def send_card(chat_id, m):
    debug(chat_id, f"CARD: {m['title']}")

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"""🎬 {m['title']}
⭐ {m['rating']}

SYSTEM OK"""
    })

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    print("========== UPDATE ==========")
    print(update)
    print("============================")

    data = load_data()

    # CALLBACK
    if "callback_query" in update:
        cb = update["callback_query"]["data"]
        chat_id = update["callback_query"]["message"]["chat"]["id"]

        debug(chat_id, f"CALLBACK: {cb}")

        if cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                send_card(chat_id, m)
            else:
                debug(chat_id, "FILM NICHT GEFUNDEN")

    # MESSAGE
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        debug(chat_id, f"MESSAGE: {msg}")

        if msg.get("text") == "/start":
            debug(chat_id, "START COMMAND ERKANNT")
            show_home(chat_id)

        else:
            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": "❗ Unbekannter Befehl"
            })

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 HARD DEBUG BOT START")

    ensure_data()

    r = requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    print("Webhook:", r.text)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))