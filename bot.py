# ================================
# 🎬 NETFLIX BOT FINAL (HERO + AUTOPLAY + FULL UI)
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
# POSTER
# ================================

def get_poster(title):
    return f"https://dummyimage.com/600x900/000/fff&text={title.replace(' ','+')}"

# ================================
# PARSER (DEIN FORMAT)
# ================================

def extract_movie(text):
    if not text:
        return None

    title = re.search(r"🎬\s*(.*?)\s*\(", text)
    year = re.search(r"\((\d{4})\)", text)
    rating = re.search(r"⭐\s*([0-9.]+)", text)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    director = re.search(r"🎥\s*(.*?)\n", text)
    story = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)
    genre = re.findall(r"#(\w+)", text)

    if not title:
        return None

    return {
        "title": title.group(1).strip(),
        "year": year.group(1) if year else "",
        "genre": genre[:2] if genre else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1) if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story.group(1).strip() if story else "-",
        "tags": genre
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
# SERIES DETECT
# ================================

def detect_series(title):
    t = title.lower()
    if "bourne" in t:
        return "Bourne"
    if "jurassic" in t:
        return "Jurassic"
    if "avengers" in t or "marvel" in t:
        return "Marvel"
    return None

# ================================
# SAVE MOVIE
# ================================

def save_movie(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie(caption)
    if not info:
        return None

    for m in data["movies"]:
        if m["title"].lower() == info["title"].lower():
            return m

    entry = {
        "id": get_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0,
        "series": detect_series(info["title"])
    }

    data["movies"].append(entry)
    save_data(data)
    return entry

# ================================
# CONTINUE WATCHING
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
# HERO BANNER
# ================================

def show_hero(chat_id, movie):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(movie["title"]),
        "caption": f"🔥 {movie['title']}",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "▶️ Abspielen", "callback_data": f"play_{movie['id']}"}
            ]]
        }
    })

# ================================
# SWIPE
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
# FULLSCREEN CARD
# ================================

def send_fullscreen(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m.get('year','')})

🔥 {' • '.join(m.get('genre',[]))}
⭐ {m.get('rating','-')} • ⏱ {m.get('runtime','-')}

🎥 {m.get('director','-')}

━━━━━━━━━━━━━━
📖 STORY
{m.get('story','-')}
━━━━━━━━━━━━━━"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Abspielen", "callback_data": f"play_{m['id']}"}],
                [{"text": "🔙 Home", "callback_data": "home"}]
            ]
        }
    })

# ================================
# AUTOPLAY NEXT
# ================================

def get_next_episode(current, data):
    if not current.get("series"):
        return None

    series = [m for m in data["movies"] if m.get("series") == current["series"]]
    series.sort(key=lambda x: x["id"])

    for i, m in enumerate(series):
        if m["id"] == current["id"] and i < len(series)-1:
            return series[i+1]

    return None

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    movies = data["movies"]

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix"
    })

    if movies:
        show_hero(chat_id, movies[-1])  # letzter Film = Banner

    cont = get_continue(chat_id, data)
    if cont:
        show_swipe(chat_id, cont)

    show_swipe(chat_id, movies[::-1])

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

                send_fullscreen(chat_id, m)

        elif cb.startswith("play_"):
            mid = cb.split("_")[1]
            m = next((x for x in data["movies"] if x["id"] == mid), None)

            if m:
                safe_post("sendVideo", {
                    "chat_id": chat_id,
                    "video": m["file_id"],
                    "caption": f"▶️ {m['title']}"
                })

                next_ep = get_next_episode(m, data)

                if next_ep:
                    safe_post("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"▶️ Nächste Folge: {next_ep['title']}",
                        "reply_markup": {
                            "inline_keyboard": [[
                                {"text": "▶️ Weiter", "callback_data": f"play_{next_ep['id']}"}
                            ]]
                        }
                    })

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            show_home(msg["chat"]["id"])

        if "video" in msg or "document" in msg:
            m = save_movie(msg)

            if m:
                safe_post("sendMessage", {
                    "chat_id": msg["chat"]["id"],
                    "text": f"✅ Gespeichert: {m['title']}"
                })

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))