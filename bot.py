# ================================
# 🎬 NETFLIX BOT FINAL (CLEAN + YOUR CARD DESIGN)
# ================================

import os
import json
import requests
import re
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

DATA_FILE = "data.json"
SESSION = {}

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

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# 🧠 PARSER (DEIN FORMAT 100%)
# ================================

def extract_movie_data(text):
    if not text:
        return None

    # TITLE + YEAR
    title = ""
    year = ""
    m = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if m:
        title = m.group(1).strip()
        year = m.group(2)

    # GENRES (🔥 ZEILE)
    genres = []
    g = re.search(r"🔥.*?•(.*?)\n", text)
    if g:
        parts = g.group(1).split("•")
        genres = [p.strip() for p in parts if p.strip()]

    # RATING
    rating = "-"
    r = re.search(r"⭐\s*([0-9\.]+)", text)
    if r:
        rating = r.group(1)

    # RUNTIME
    runtime = "-"
    rt = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    if rt:
        runtime = rt.group(1)

    # DIRECTOR
    director = "-"
    d = re.search(r"🎥\s*(.*?)\n", text)
    if d:
        director = d.group(1).strip()

    # STORY
    story = "-"
    s = re.search(r"📖 STORY\s*(.*?)━━━━━━━━", text, re.DOTALL)
    if s:
        story = s.group(1).strip()

    if not title:
        return None

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
# 📊 SCORE SYSTEM
# ================================

def get_score(m):
    return m.get("views", 0) * 1.5

def get_top_movies(data):
    return sorted(data["movies"], key=get_score, reverse=True)[:10]

# ================================
# 🎮 SWIPE UI
# ================================

def show_swipe(chat_id, movies, i=0):
    SESSION[chat_id] = movies

    if not movies:
        return

    m = movies[i]

    nav = []
    if i > 0:
        nav.append({"text": "⬅️", "callback_data": f"swipe_{i-1}"})
    if i < len(movies)-1:
        nav.append({"text": "➡️", "callback_data": f"swipe_{i+1}"})

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"🎬 {m['title']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎬 CARD (DEIN DESIGN)
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m.get('year','')})
🔥 4K • {' • '.join(m.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {m.get('rating','-')} • ⏱ {m.get('runtime','-')} • 🔞 FSK 16
🎥 {m.get('director','-')}
━━━━━━━━━━━━━━
📖 STORY
{m.get('story','-')}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━
#{' #'.join(m.get('genre',[]))} #Neu
@LibraryOfLegends"""

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m["file_id"],
        "caption": caption
    })

# ================================
# 💾 SAVE MOVIE
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
        "id": get_next_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)
    return entry

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Clean Netflix System"
    })

    show_swipe(chat_id, get_top_movies(data))

# ================================
# VIDEO HANDLER
# ================================

def handle_video(msg):
    m = save_movie(msg)

    if not m:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Bitte dein Film-Template verwenden!"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"✅ Gespeichert: {m['title']}"
    })

    send_card(msg["chat"]["id"], m)
    send_card(CHANNEL, m)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    data = load_data()

    if "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        cb = update["callback_query"]["data"]

        if cb.startswith("swipe_"):
            i = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), i)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if m:
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            show_home(msg["chat"]["id"])

        if "video" in msg or "document" in msg:
            handle_video(msg)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))