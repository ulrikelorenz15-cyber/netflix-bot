# ================================
# 🎬 NETFLIX BOT FINAL BOSS MODE
# ================================

import os
import json
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
OMDB_KEY = "a3776f86"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"

# ================================
# DATA
# ================================

def load_data():
    default = {
        "movies": [],
        "categories": {},
        "collections": {},
        "series": {}
    }

    if os.path.exists(DATA_FILE):
        try:
            data = json.load(open(DATA_FILE))
            for k in default:
                if k not in data:
                    data[k] = default[k]
            return data
        except:
            return default

    return default

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

# ================================
# FILM ID
# ================================

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# OMDb
# ================================

def get_movie(title):
    try:
        r = requests.get(f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full").json()
        if r.get("Response") == "False":
            return None
        return r
    except:
        return None

# ================================
# KI STORY
# ================================

def generate_story(title, plot, genre):
    try:
        if not plot or plot == "N/A":
            plot = f"{title} ist ein Film aus dem Genre {genre}."

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Schreibe eine deutsche Netflix Filmbeschreibung (2-3 Sätze, konkret, realistisch): {plot}"
            }]
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 40:
            raise Exception()

        return text

    except:
        return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte, Druck und Konsequenzen, bei der jede Entscheidung neue Folgen hat."

# ================================
# AUTO COLLECTIONS
# ================================

def build_auto_collections(data):
    collections = {
        "🔥 Beste Action": [],
        "🧠 Mystery": [],
        "😂 Komödie": [],
        "🚀 Sci-Fi": [],
        "👑 Top IMDb": []
    }

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        genre = movie.get("Genre", "").lower()
        rating = float(movie.get("imdbRating", "0"))

        if "action" in genre:
            collections["🔥 Beste Action"].append(m)

        if "mystery" in genre or "thriller" in genre:
            collections["🧠 Mystery"].append(m)

        if "comedy" in genre:
            collections["😂 Komödie"].append(m)

        if "sci-fi" in genre:
            collections["🚀 Sci-Fi"].append(m)

        if rating >= 7.5:
            collections["👑 Top IMDb"].append(m)

    return collections

# ================================
# SERIES
# ================================

SERIES = {
    "Bourne": ["Bourne Identity", "Bourne Supremacy", "Bourne Ultimatum"],
    "John Wick": ["John Wick", "Chapter 2", "Chapter 3", "Chapter 4"],
}

def detect_series(title):
    for name, arr in SERIES.items():
        for a in arr:
            if a.lower() in title.lower():
                return name
    return None

# ================================
# GRID (SWIPE UI)
# ================================

def show_grid(chat_id, movies, page=0):
    per_page = 3
    start = page * per_page
    end = start + per_page

    subset = movies[start:end]

    for m in subset:
        movie = get_movie(m["title"])
        if not movie:
            continue

        caption = f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}"

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"],
            "caption": caption,
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ Öffnen", "callback_data": f"movie_{movie['Title']}"}
                ]]
            }
        })

    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"grid_{page-1}"})
    if end < len(movies):
        nav.append({"text": "➡️", "callback_data": f"grid_{page+1}"})

    buttons = [nav] if nav else []
    buttons.append([{"text": "🏠 Home", "callback_data": "home"}])

    send_buttons(chat_id, "🎬 Browse", buttons)

# ================================
# UI
# ================================

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_buttons(chat_id, text, buttons):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons}
    })

def show_home(chat_id):
    send_buttons(chat_id, "🎬 Library of Legends", [
        [
            {"text": "🔥 Trending", "callback_data": "trending"},
            {"text": "🆕 Neu", "callback_data": "new"}
        ],
        [
            {"text": "⭐ Top IMDb", "callback_data": "top"},
            {"text": "🎞 Collections", "callback_data": "collections"}
        ],
        [
            {"text": "🎬 Genres", "callback_data": "genres"},
            {"text": "🎬 Reihen", "callback_data": "series"}
        ]
    ])

# ================================
# FILM CARD
# ================================

def send_film_card(chat_id, movie, file_id, movie_id):
    genre = " • ".join(movie["Genre"].split(","))
    actors = ", ".join(movie["Actors"].split(", ")[:3])

    plot = generate_story(movie["Title"], movie.get("Plot", ""), movie["Genre"])

    caption = f"""🎬 {movie["Title"].upper()} ({movie["Year"]})
🔥 4K • {genre}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
🎭 {actors}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{movie_id}
━━━━━━━━━━━━━━"""

    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": movie["Poster"]
    })

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": file_id,
        "caption": caption
    })

# ================================
# VIDEO UPLOAD
# ================================

def handle_video(message):
    data = load_data()

    video = message.get("video") or message.get("document")
    title = message.get("caption", "Unknown")

    movie = get_movie(title)
    if not movie:
        return

    movie_id = get_next_id(data)

    entry = {
        "id": movie_id,
        "title": movie["Title"],
        "file_id": video["file_id"],
        "genre": movie["Genre"],
        "views": 0
    }

    data["movies"].append(entry)

    save_data(data)

    send_film_card(message["chat"]["id"], movie, video["file_id"], movie_id)
    send_film_card(CHANNEL, movie, video["file_id"], movie_id)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        data_cb = update["callback_query"]["data"]
        data = load_data()

        if data_cb == "home":
            show_home(chat_id)

        elif data_cb == "trending":
            show_grid(chat_id, data["movies"], 0)

        elif data_cb == "new":
            show_grid(chat_id, list(reversed(data["movies"])), 0)

        elif data_cb == "top":
            auto = build_auto_collections(data)
            show_grid(chat_id, auto["👑 Top IMDb"], 0)

        elif data_cb == "collections":
            auto = build_auto_collections(data)
            buttons = [[{"text": k, "callback_data": f"auto_{k}"}] for k in auto]
            send_buttons(chat_id, "🎞 Collections", buttons)

        elif data_cb.startswith("auto_"):
            auto = build_auto_collections(data)
            name = data_cb.replace("auto_", "")
            show_grid(chat_id, auto.get(name, []), 0)

        elif data_cb.startswith("movie_"):
            title = data_cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if m:
                movie = get_movie(title)
                send_film_card(chat_id, movie, m["file_id"], m["id"])

        elif data_cb.startswith("grid_"):
            page = int(data_cb.split("_")[1])
            show_grid(chat_id, data["movies"], page)

        return "ok"

    message = update.get("message")

    if message and ("video" in message or "document" in message):
        handle_video(message)

    if message and message.get("text") == "/start":
        show_home(message["chat"]["id"])

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))