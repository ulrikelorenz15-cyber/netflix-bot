# ================================
# 🎬 NETFLIX BOT FINAL (ULTRA UI)
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
USER_STATE = {}

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except:
        pass

# ================================
# 🎬 POSTER (REAL STYLE)
# ================================

def get_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+cinematic+movie+poster+dark"

# ================================
# 🧠 SERIES DETECTION
# ================================

def detect_series(title):
    t = title.lower()

    if "bourne" in t:
        return "Bourne"
    if "jurassic" in t:
        return "Jurassic"
    if "star trek" in t:
        return "Star Trek"
    if "godzilla" in t or "kong" in t:
        return "MonsterVerse"
    if "marvel" in t or "avenger" in t or "deadpool" in t:
        return "Marvel"

    return None

# ================================
# 🧠 PARSER (PERFECT)
# ================================

def extract_movie_data(text):
    if not text:
        return None

    m = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not m:
        return None

    title = m.group(1).strip()
    year = m.group(2)

    rating = re.search(r"⭐\s*([0-9.]+)", text)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    director = re.search(r"🎥\s*(.*?)\n", text)

    story = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)

    genres = re.findall(r"#(\w+)", text)
    if not genres:
        g = re.search(r"🔥.*?•(.*?)\n", text)
        if g:
            genres = [x.strip() for x in g.group(1).split("•")]

    return {
        "title": title,
        "year": year,
        "genre": genres[:2] if genres else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1) if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story.group(1).strip() if story else "-",
        "tags": genres if genres else [],
        "series": detect_series(title)
    }

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
# SAVE MOVIE
# ================================

def save_movie(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie_data(caption)
    if not info:
        return None

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
# 📊 SCORE
# ================================

def get_score(m):
    return m["views"] * 2 + len(m["genre"]) * 2

def get_top_movies(data):
    return sorted(data["movies"], key=get_score, reverse=True)[:10]

# ================================
# 📂 STRUCTURE
# ================================

def get_categories(data):
    cats = {}
    for m in data["movies"]:
        for g in m["genre"]:
            cats.setdefault(g, []).append(m)
    return cats

def get_series(data):
    s = {}
    for m in data["movies"]:
        if m.get("series"):
            s.setdefault(m["series"], []).append(m)
    return s

# ================================
# ▶️ CONTINUE WATCHING
# ================================

def update_continue(uid, mid):
    USER_STATE.setdefault(uid, [])

    if mid in USER_STATE[uid]:
        USER_STATE[uid].remove(mid)

    USER_STATE[uid].insert(0, mid)
    USER_STATE[uid] = USER_STATE[uid][:5]

def get_continue(uid, data):
    ids = USER_STATE.get(uid, [])
    return [m for m in data["movies"] if m["id"] in ids]

# ================================
# 🎮 SWIPE UI (NETFLIX STYLE)
# ================================

def show_swipe(chat_id, movies, index=0):
    SESSION[chat_id] = movies

    if not movies:
        return

    m = movies[index]

    nav = []
    if index > 0:
        nav.append({"text": "⬅️", "callback_data": f"swipe_{index-1}"})
    if index < len(movies)-1:
        nav.append({"text": "➡️", "callback_data": f"swipe_{index+1}"})

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"🎬 {m['title']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎬 FULL CARD
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m['year']})
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
{' '.join(['#'+g for g in m['tags']])}
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"])
    })

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m["file_id"],
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Start", "callback_data": f"play_{m['id']}"}],
                [{"text": "🏠 Home", "callback_data": "home"}]
            ]
        }
    })

# ================================
# 🏠 HOME (ULTRA NETFLIX)
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 ULTRA NETFLIX UI"
    })

    # HERO
    show_swipe(chat_id, get_top_movies(data), 0)

    # CONTINUE
    cont = get_continue(chat_id, data)
    if cont:
        show_swipe(chat_id, cont, 0)

    # SERIES
    for name, movies in get_series(data).items():
        show_swipe(chat_id, movies, 0)

    # GENRES
    for name, movies in get_categories(data).items():
        show_swipe(chat_id, movies[:10], 0)

# ================================
# VIDEO
# ================================

def handle_video(msg):
    entry = save_movie(msg)

    if not entry:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Format falsch!"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"✅ Gespeichert: {entry['title']}"
    })

    send_card(msg["chat"]["id"], entry)
    send_card(CHANNEL, entry)

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

        if cb == "home":
            show_home(chat_id)

        elif cb.startswith("swipe_"):
            i = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), i)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                update_continue(chat_id, m["id"])
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

        elif cb.startswith("play_"):
            mid = cb.split("_")[1]
            m = next((x for x in data["movies"] if x["id"] == mid), None)

            if m:
                safe_post("sendVideo", {
                    "chat_id": chat_id,
                    "video": m["file_id"],
                    "caption": f"▶️ {m['title']}"
                })

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