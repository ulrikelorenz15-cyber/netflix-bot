# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE OFFLINE NETFLIX SYSTEM + FULL UPGRADE)
# ================================

import os
import json
import requests
import re
from flask import Flask, request
from openai import OpenAI
from difflib import get_close_matches

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
USERS_FILE = "users.json"

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
# 👤 PROFILE SYSTEM
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
            "profiles": {
                "default": {
                    "watching": [],
                    "history": [],
                    "favorites": []
                }
            },
            "active": "default"
        }
        save_users(users)

    return users[str(uid)]

def get_profile(uid):
    user = get_user(uid)
    return user["profiles"][user["active"]]

# ================================
# 🧠 AI GENRE
# ================================

def ai_detect_genre(title):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Genres für Film: {title}. Nur 2 Genres."
            }]
        )
        return [g.strip() for g in res.choices[0].message.content.split(",")]
    except:
        return ["Unknown"]

# ================================
# 🎬 POSTER
# ================================

def generate_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

# ================================
# 🎞 MARVEL PHASE
# ================================

def detect_marvel_phase(title):
    t = title.lower()
    if "avengers" in t or "iron man" in t:
        return "Phase 1"
    if "ultron" in t:
        return "Phase 2"
    if "infinity" in t or "endgame" in t:
        return "Phase 3"
    return None

# ================================
# 🧠 AUTO DB BUILDER
# ================================

def extract_movie_data(text):
    if not text:
        return None

    text = text.replace("\n", " ")

    title = "Unknown"
    year = ""

    m = re.search(r"🎬\s*(.*?)\s*\((\d{4})?\)", text)
    if m:
        title = m.group(1).strip()
        year = m.group(2) or ""

    genres = re.findall(r"#(\w+)", text)
    if not genres:
        genres = ai_detect_genre(title)

    runtime = "-"
    rt = re.search(r"⏱\s*([0-9]+ ?min)", text.lower())
    if rt:
        runtime = rt.group(1)

    director = "-"
    dr = re.search(r"🎥\s*([^#]+)", text)
    if dr:
        director = dr.group(1).strip()

    return {
        "title": title,
        "year": year,
        "genre": genres[:2],
        "runtime": runtime,
        "director": director,
        "rating": "-"
    }

def save_movie_from_post(msg):
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
        "id": get_next_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0,
        "phase": detect_marvel_phase(info["title"])
    }

    data["movies"].append(entry)
    save_data(data)
    return entry

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
# 📊 SCORE SYSTEM
# ================================

def get_score(m):
    return m.get("views", 0) * 1.5 + len(m.get("genre", [])) * 2

def get_top_movies(data):
    return sorted(data["movies"], key=get_score, reverse=True)[:10]

# ================================
# 📂 AUTO CATEGORIES
# ================================

def get_categories(data):
    categories = {}

    for m in data["movies"]:
        for g in m.get("genre", []):
            categories.setdefault(g, []).append(m)

    return categories

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
        "photo": generate_poster(m["title"]),
        "caption": f"🎬 {m['title']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# UI
# ================================

def show_row(chat_id, title, movies):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    buttons = [[{
        "text": m["title"][:15],
        "callback_data": f"movie_{m['title']}"
    } for m in movies[:5]]]

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": " ",
        "reply_markup": {"inline_keyboard": buttons}
    })

# ================================
# 🎬 CARD
# ================================

def send_card(chat_id, movie):
    phase = f"\n🧬 {movie['phase']}" if movie.get("phase") else ""

    caption = f"""🎬 {movie['title'].upper()} ({movie.get('year','')})
🔥 4K • {' • '.join(movie.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {movie.get('rating','-')} • ⏱ {movie.get('runtime','-')}
🎥 {movie.get('director','-')}{phase}
━━━━━━━━━━━━━━
▶️ #{movie['id']}
━━━━━━━━━━━━━━
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": generate_poster(movie["title"])
    })

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": movie["file_id"],
        "caption": caption
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix System"
    })

    show_swipe(chat_id, get_top_movies(data))
    show_row(chat_id, "🆕 Neu", list(reversed(data["movies"]))[:10])

    categories = get_categories(data)
    for name, movies in categories.items():
        show_row(chat_id, f"🎬 {name}", movies[:10])

# ================================
# VIDEO
# ================================

def handle_video(msg):
    entry = save_movie_from_post(msg)

    if not entry:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Fehler beim Erkennen"
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
            index = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), index)

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