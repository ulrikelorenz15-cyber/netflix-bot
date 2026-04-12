# ================================
# 🎬 NETFLIX BOT (FINAL FIXED CORE)
# ================================

import os
import json
import requests
import re
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except:
        pass

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
# 🧠 PERFECT PARSER (DEIN FORMAT)
# ================================

def extract_movie_data(text):
    if not text:
        return None

    # TITLE + YEAR
    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t:
        return None

    title = t.group(1).strip()
    year = t.group(2)

    # RATING
    rating = "-"
    r = re.search(r"⭐\s*([0-9.]+)", text)
    if r:
        rating = r.group(1)

    # RUNTIME
    runtime = "-"
    rt = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    if rt:
        runtime = rt.group(1)

    # DIRECTOR
    director = "-"
    dr = re.search(r"🎥\s*(.*?)\n", text)
    if dr:
        director = dr.group(1).strip()

    # STORY
    story = "-"
    st = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)
    if st:
        story = st.group(1).strip()

    # GENRE
    genres = re.findall(r"#(\w+)", text)
    if not genres:
        g = re.search(r"🔥.*?•(.*?)\n", text)
        if g:
            genres = [x.strip() for x in g.group(1).split("•")]

    return {
        "title": title,
        "year": year,
        "genre": genres[:2] if genres else ["Unknown"],
        "runtime": runtime,
        "director": director,
        "rating": rating,
        "story": story
    }

# ================================
# SAVE MOVIE
# ================================

def save_movie(msg):
    data = load_data()

    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie_data(caption)

    if not info:
        return None

    # DUPLICATE CHECK
    for m in data["movies"]:
        if m["title"].lower() == info["title"].lower():
            return m

    entry = {
        "id": get_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)

    return entry

# ================================
# CARD
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title']} ({m['year']})
🔥 4K • {' • '.join(m['genre'])}
━━━━━━━━━━━━━━
⭐ {m['rating']} • ⏱ {m['runtime']} • 🔞 FSK 16
🎥 {m['director']}
━━━━━━━━━━━━━━
📖 STORY
{m['story']}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━
{' '.join(['#'+g for g in m['genre']])}
@LibraryOfLegends"""

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m["file_id"],
        "caption": caption
    })

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    print("UPDATE:", update)

    # MESSAGE
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        # START
        if msg.get("text") == "/start":
            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": "🔥 Bot ist bereit – sende einen Film"
            })

        # 🔥 VIDEO HANDLER (FIX!)
        if "video" in msg or "document" in msg:
            entry = save_movie(msg)

            if not entry:
                safe_post("sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Film konnte nicht erkannt werden"
                })
                return "ok"

            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ Gespeichert: {entry['title']}"
            })

            send_card(chat_id, entry)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 FINAL FIXED BOT RUNNING")

    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))