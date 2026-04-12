# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE FINAL VERSION)
# ================================

import os
import json
import requests
import re
from flask import Flask, request
from difflib import get_close_matches

TOKEN = os.getenv("BOT_TOKEN")
TMDB_KEY = os.getenv("TMDB_KEY")
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
# 🎬 REAL POSTER (TMDB)
# ================================

def get_poster(title):
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={title}"
        res = requests.get(url, timeout=5).json()

        if res["results"]:
            path = res["results"][0].get("poster_path")
            if path:
                return f"https://image.tmdb.org/t/p/w500{path}"
    except:
        pass

    return f"https://dummyimage.com/600x900/000/fff&text={title}"

# ================================
# 🧠 PARSER (ULTRA FIX)
# ================================

def extract_movie_data(text):
    if not text:
        return None

    title_match = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not title_match:
        return None

    title = title_match.group(1).strip()
    year = title_match.group(2)

    rating = re.search(r"⭐\s*([0-9.]+)", text)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    director = re.search(r"🎥\s*(.*?)\n", text)
    story = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)

    genres = re.findall(r"#(\w+)", text)

    return {
        "title": title,
        "year": year,
        "genre": genres[:2] if genres else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1).strip() if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story.group(1).strip() if story else "-",
        "tags": genres if genres else ["Unknown"]
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

def get_top_movies(data):
    return sorted(data["movies"], key=lambda x: x["views"], reverse=True)[:10]

# ================================
# ▶️ CONTINUE
# ================================

def update_continue(uid, mid):
    USER_STATE.setdefault(uid, [])
    if mid in USER_STATE[uid]:
        USER_STATE[uid].remove(mid)
    USER_STATE[uid].insert(0, mid)

def get_continue(uid, data):
    ids = USER_STATE.get(uid, [])
    return [m for m in data["movies"] if m["id"] in ids]

# ================================
# 🎮 PREVIEW (HOVER FAKE)
# ================================

def send_preview(chat_id, m):
    for i in range(2):
        safe_post("sendPhoto", {
            "chat_id": chat_id,
            "photo": f"https://image.pollinations.ai/prompt/{m['title']}+scene+{i}",
            "caption": f"🎬 Preview: {m['title']}"
        })

# ================================
# 🎮 SWIPE UI
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
        "caption": f"{m['title']}\n⭐ {m['rating']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎬 CARD
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
        "caption": caption
    })

# ================================
# 🏠 HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Netflix Style UI"
    })

    top = get_top_movies(data)

    if top:
        show_swipe(chat_id, top, 0)

# ================================
# VIDEO
# ================================

def handle_video(msg):
    entry = save_movie(msg)

    if not entry:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Fehler beim Erkennen"
        })
        return

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

        if cb.startswith("swipe_"):
            i = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), i)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                send_preview(chat_id, m)
                update_continue(chat_id, m["id"])
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