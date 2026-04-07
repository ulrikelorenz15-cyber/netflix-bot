# ================================
# 🎬 TELEGRAM BOT (NO LIBRARY FIX)
# ================================

import os
import json
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

data = load_data()

# ---------------- SEND MESSAGE ----------------
def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# ---------------- START ----------------
def handle_start(chat_id):
    send_message(chat_id, "🎬 Library of Legends\n\nSchick mir ein Video!")

# ---------------- VIDEO ----------------
def handle_video(chat_id, message):
    video = message.get("video") or message.get("document")

    title = message.get("caption", "Unknown")

    file_id = video["file_id"]

    new_id = len(data["movies"]) + 1

    # einfache Fake Daten (später verbessern)
    year = "2025"
    genre = "Action • Thriller"
    rating = round(6.5 + new_id * 0.1, 1)
    runtime = 100 + new_id
    fsk = "16"

    caption = f"""🎬 {title.upper()} ({year})
🔥 4K • {genre}
━━━━━━━━━━━━━━
⭐ {rating} • ⏱ {runtime} Min • 🔞 FSK {fsk}
━━━━━━━━━━━━━━
📖 STORY
Ein spannender Film voller Action und Wendungen.
━━━━━━━━━━━━━━
▶️ #{str(new_id).zfill(4)}
━━━━━━━━━━━━━━
#Action #Thriller #Neu
@LibraryOfLegends"""

    data["movies"].append({
        "id": new_id,
        "title": title,
        "file_id": file_id
    })

    save_data(data)

    # VIDEO POSTEN
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": file_id,
        "caption": caption
    })

# ---------------- SEARCH ----------------
def handle_text(chat_id, text):
    results = [m for m in data["movies"] if text.lower() in m["title"].lower()]

    if not results:
        send_message(chat_id, "❌ Kein Film gefunden")
        return

    msg = "🎬 Ergebnisse:\n\n"

    for m in results:
        msg += f"{m['title']}\n"

    send_message(chat_id, msg)

# ---------------- WEBHOOK ----------------
app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message:
        if message["text"] == "/start":
            handle_start(chat_id)
        else:
            handle_text(chat_id, message["text"])

    elif "video" in message or "document" in message:
        handle_video(chat_id, message)

    return "ok"

@app.route("/")
def home():
    return "🤖 Bot läuft!"

# ---------------- START ----------------
if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")

    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")

    app.run(host="0.0.0.0", port=8080)