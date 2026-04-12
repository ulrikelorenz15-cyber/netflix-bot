# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE OFFLINE NETFLIX SYSTEM)
# ================================

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from difflib import get_close_matches

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
USERS_FILE = "users.json"

CACHE = {}
SESSION = {}

# ================================
# UTILS
# ================================

def log_error(e):
    print("ERROR:", str(e))

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except Exception as e:
        log_error(e)

def clean_title(raw):
    if not raw:
        return ""
    raw = raw.replace(".", " ")
    blacklist = ["1080p","720p","bluray","x264","x265","dvdrip","webdl"]
    return " ".join([w for w in raw.split() if w.lower() not in blacklist])

# ================================
# 🧠 USER SYSTEM
# ================================

def load_users():
    if os.path.exists(USERS_FILE):
        return json.load(open(USERS_FILE))
    return {}

def save_users(users):
    json.dump(users, open(USERS_FILE, "w"))

def get_user(uid):
    users = load_users()
    if str(uid) not in users:
        users[str(uid)] = {
            "watching": [],
            "history": [],
            "favorites": []
        }
        save_users(users)
    return users[str(uid)]

def update_continue(uid, movie_id):
    users = load_users()
    user = get_user(uid)

    if movie_id in user["watching"]:
        user["watching"].remove(movie_id)

    user["watching"].insert(0, movie_id)
    user["watching"] = user["watching"][:5]

    if movie_id not in user["history"]:
        user["history"].append(movie_id)

    users[str(uid)] = user
    save_users(users)

def add_favorite(uid, movie_id):
    users = load_users()
    user = get_user(uid)

    if movie_id not in user["favorites"]:
        user["favorites"].append(movie_id)

    users[str(uid)] = user
    save_users(users)

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return json.load(open(DATA_FILE))
        except:
            return {"movies": []}
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# 🧠 MATCH SYSTEM (OFFLINE)
# ================================

def match_movie(raw, data):
    raw = raw.lower()

    # DIRECT
    for m in data["movies"]:
        if raw in m["title"].lower():
            return m

    # FUZZY
    titles = [m["title"] for m in data["movies"]]
    match = get_close_matches(raw, titles, n=1, cutoff=0.5)

    if match:
        return next((x for x in data["movies"] if x["title"] == match[0]), None)

    return None

# ================================
# 📊 TRENDING
# ================================

def get_top_movies(data):
    return sorted(data["movies"], key=lambda x: x.get("views", 0), reverse=True)[:10]

# ================================
# 🧠 RECOMMENDATIONS
# ================================

def get_recommendations(uid, data):
    user = get_user(uid)

    genres = []

    for mid in user["history"]:
        m = next((x for x in data["movies"] if x["id"] == mid), None)
        if m:
            genres += m.get("genre", [])

    scored = []

    for m in data["movies"]:
        score = 0

        for g in m.get("genre", []):
            if g in genres:
                score += 2

        score += m.get("views", 0) * 0.2

        scored.append((score, m))

    scored.sort(reverse=True)
    return [m for _, m in scored[:10]]

# ================================
# 🎞 ROW UI
# ================================

def show_row(chat_id, title, movies):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    buttons = []
    for m in movies[:5]:
        buttons.append({
            "text": m["title"][:15],
            "callback_data": f"movie_{m['title']}"
        })

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": " ",
        "reply_markup": {"inline_keyboard": [buttons]}
    })

# ================================
# 🎬 CARD
# ================================

def send_card(chat_id, movie):
    caption = f"""🎬 {movie['title'].upper()} ({movie.get('year','')})
🔥 4K • {' • '.join(movie.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {movie.get('rating','-')} • ⏱ {movie.get('runtime','-')}
🎥 {movie.get('director','-')}
━━━━━━━━━━━━━━
▶️ #{movie['id']}
━━━━━━━━━━━━━━
@LibraryOfLegends"""

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": movie["file_id"],
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Starten", "callback_data": f"play_{movie['id']}"}],
                [{"text": "⭐ Favorit", "callback_data": f"fav_{movie['id']}"}],
                [{"text": "🏠 Home", "callback_data": "home"}]
            ]
        }
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    user = get_user(chat_id)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Dein Netflix"
    })

    if user["watching"]:
        movies = [m for m in data["movies"] if m["id"] in user["watching"]]
        show_row(chat_id, "▶️ Weiter schauen", movies)

    show_row(chat_id, "🔥 Trending", get_top_movies(data))
    show_row(chat_id, "🧠 Für dich", get_recommendations(chat_id, data))
    show_row(chat_id, "🆕 Neu", list(reversed(data["movies"]))[:10])

# ================================
# VIDEO
# ================================

def handle_video(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    raw = clean_title(msg.get("caption") or "")
    movie = match_movie(raw, data)

    if not movie:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": f"❌ Nicht erkannt: {raw}"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"🧠 Erkannt: {movie['title']}"
    })

    send_card(msg["chat"]["id"], movie)
    send_card(CHANNEL, movie)

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

        elif cb.startswith("play_"):
            mid = cb.split("_")[1]
            update_continue(chat_id, mid)

            m = next((x for x in data["movies"] if x["id"] == mid), None)
            if m:
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

        elif cb.startswith("fav_"):
            mid = cb.split("_")[1]
            add_favorite(chat_id, mid)

            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": "⭐ Zu Favoriten hinzugefügt"
            })

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if m:
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