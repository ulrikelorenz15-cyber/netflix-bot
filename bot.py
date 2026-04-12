# ================================
# 🎬 NETFLIX BOT FINAL (ULTRA GOD MODE + HOME UI)
# ================================

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
OMDB_KEY = "a3776f86"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
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
# LOCAL MATCH
# ================================

LOCAL_DB = {
    "bourne": "The Bourne Identity",
    "jurassic": "Jurassic Park"
}

def local_match(title):
    t = title.lower()
    for key in LOCAL_DB:
        if key in t:
            return LOCAL_DB[key]
    return None

# ================================
# AI
# ================================

def ai_detect_title(raw_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":raw_text}]
        )
        return res.choices[0].message.content.strip()
    except:
        return None

# ================================
# OMDb
# ================================

def get_movie(title):
    if title in CACHE:
        return CACHE[title]

    try:
        r = requests.get(
            f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}",
            timeout=5
        ).json()

        if r.get("Response") == "False":
            return None

        CACHE[title] = r
        return r
    except:
        return None

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
# RANKING
# ================================

def get_rankings(data):
    movies = data["movies"]

    return {
        "🔥 Trending": sorted(movies, key=lambda x: x.get("views", 0), reverse=True)[:10],
        "🆕 Neu": list(reversed(movies))[:10]
    }

# ================================
# SERIES
# ================================

def detect_series(title):
    t = title.lower()
    if "bourne" in t:
        return "Bourne"
    if "jurassic" in t:
        return "Jurassic"
    return None

def get_series_list(data, name):
    return [m for m in data["movies"] if m.get("series") == name]

# ================================
# UI GRID
# ================================

def show_grid(chat_id, movies):
    SESSION[chat_id] = movies

    for m in movies[:3]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        safe_post("sendPhoto", {
            "chat_id": chat_id,
            "photo": movie.get("Poster"),
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ Öffnen", "callback_data": f"movie_{movie['Title']}"}
                ]]
            }
        })

# ================================
# SERIES ROW
# ================================

def show_series_row(chat_id, data):
    series = list(set([m.get("series") for m in data["movies"] if m.get("series")]))

    buttons = []
    for s in series:
        buttons.append([{"text": f"🎞 {s}", "callback_data": f"series_{s}"}])

    if buttons:
        safe_post("sendMessage", {
            "chat_id": chat_id,
            "text": "🎞 Reihen",
            "reply_markup": {"inline_keyboard": buttons}
        })

# ================================
# HOME UI
# ================================

def show_home(chat_id):
    data = load_data()
    rankings = get_rankings(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix Style"
    })

    safe_post("sendMessage", {"chat_id": chat_id, "text": "🔥 Trending"})
    show_grid(chat_id, rankings["🔥 Trending"])

    safe_post("sendMessage", {"chat_id": chat_id, "text": "🆕 Neu"})
    show_grid(chat_id, rankings["🆕 Neu"])

    show_series_row(chat_id, data)

# ================================
# CARD
# ================================

def send_card(chat_id, movie, local):
    caption = f"""🎬 {movie['Title']} ({movie['Year']})
⭐ {movie['imdbRating']} • ⏱ {movie.get('Runtime')}
▶️ #{local['id']}"""

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption
    })

# ================================
# VIDEO
# ================================

def handle_video(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    raw = clean_title(msg.get("caption") or "")

    movie = None

    if raw:
        local = local_match(raw)
        if local:
            movie = get_movie(local)

    if not movie:
        movie = get_movie(raw)

    if not movie:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": f"❌ Nicht erkannt: {raw}"
        })
        return

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0,
        "series": detect_series(movie["Title"])
    }

    data["movies"].append(entry)
    save_data(data)

    send_card(msg["chat"]["id"], movie, entry)
    send_card(CHANNEL, movie, entry)

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

        if cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                movie = get_movie(title)
                m["views"] += 1
                save_data(data)
                send_card(chat_id, movie, m)

        elif cb.startswith("series_"):
            name = cb.replace("series_", "")
            show_grid(chat_id, get_series_list(data, name))

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