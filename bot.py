# ================================
# 🎬 TELEGRAM BOT (ULTIMATE NETFLIX UI)
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"

# ================================
# DATA
# ================================

def load_data():
    default = {
        "movies": [],
        "categories": {},
        "years": {},
        "series": {}
    }

    if os.path.exists(DATA_FILE):
        try:
            data = json.load(open(DATA_FILE))

            # 🔥 fehlende Keys automatisch ergänzen
            for key in default:
                if key not in data:
                    data[key] = default[key]

            return data
        except:
            return default

    return default

# ================================
# KI STORY (GENRE STYLE)
# ================================

def generate_story(title, plot, genre):
    try:
        style = "realistisch"
        g = genre.lower()

        if "horror" in g:
            style = "düster und bedrohlich"
        elif "action" in g:
            style = "intensiv und schnell"
        elif "drama" in g:
            style = "emotional und tief"
        elif "crime" in g:
            style = "düster und spannend"

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine realistische deutsche Netflix-Beschreibung.

Film: {title}
Genre: {genre}
Stil: {style}

Inhalt:
{plot}

4-6 Sätze. Keine Floskeln.
"""
            }],
            temperature=1.1
        )

        return response.choices[0].message.content.strip()

    except:
        return plot

# ================================
# OMDb
# ================================

def get_movie_data(title):
    try:
        url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full"
        data = requests.get(url).json()
        if data.get("Response") == "False":
            return None
        return data
    except:
        return None

# ================================
# SORTIERUNG
# ================================

def categorize_movie(movie):
    genres = movie["genre"].split(",")

    for g in genres:
        g = g.strip()
        data["categories"].setdefault(g, []).append(movie["title"])

    year = int(movie["year"]) if movie["year"].isdigit() else 2025

    if year >= 2020:
        group = "2020-2025"
    elif year >= 2010:
        group = "2010-2019"
    else:
        group = "2000-2009"

    data["years"].setdefault(group, []).append(movie["title"])

    series = detect_series(movie["title"])
    if series:
        name = series.split(" ", 1)[1]
        data["series"].setdefault(name, []).append(movie["title"])

# ================================
# REIHEN
# ================================

def detect_series(title):
    t = title.lower()

    if "avengers" in t:
        return "🔥 Marvel"
    if "fast" in t:
        return "🚗 Fast & Furious"
    if "star wars" in t:
        return "🌌 Star Wars"

    return ""

# ================================
# UI
# ================================

def send_buttons(chat_id, text, buttons):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons}
    })

def show_home(chat_id):
    buttons = [
        [{"text": "🎬 Genres", "callback_data": "genres"}],
        [{"text": "📅 Jahre", "callback_data": "years"}],
        [{"text": "🎞 Reihen", "callback_data": "series"}]
    ]
    send_buttons(chat_id, "🎬 Library UI", buttons)

# ================================
# LISTEN
# ================================

def show_movies(chat_id, movies):
    buttons = []
    for m in movies[:10]:
        buttons.append([{"text": m, "callback_data": f"movie_{m}"}])

    buttons.append([{"text": "🔙", "callback_data": "home"}])

    send_buttons(chat_id, "🎬 Filme:", buttons)

# ================================
# FILM CARD
# ================================

def show_movie_card(chat_id, title):
    movie_local = next((m for m in data["movies"] if m["title"] == title), None)

    if not movie_local:
        return

    movie = get_movie_data(title)

    if movie:
        genre = movie.get("Genre", "")
        plot = generate_story(title, movie.get("Plot", ""), genre)
        actors = movie.get("Actors", "")
        rating = movie.get("imdbRating", "")
        runtime = movie.get("Runtime", "")
        director = movie.get("Director", "")
        poster = movie.get("Poster")
        year = movie.get("Year")
    else:
        return

    caption = f"""🎬 {title.upper()} ({year})
🔥 {genre}
━━━━━━━━━━━━━━
⭐ {rating} • ⏱ {runtime}
🎥 {director}
🎭 {actors.split(",")[0:2]}
━━━━━━━━━━━━━━
📖 {plot}
━━━━━━━━━━━━━━"""

    if poster and poster != "N/A":
        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": poster
        })

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": movie_local["file_id"],
        "caption": caption
    })

# ================================
# VIDEO UPLOAD
# ================================

def handle_video(chat_id, message):
    video = message.get("video") or message.get("document")
    title = message.get("caption", "Unknown")

    file_id = video["file_id"]

    movie = get_movie_data(title)

    if not movie:
        return

    title = movie.get("Title")
    year = movie.get("Year")
    genre = movie.get("Genre")

    data["movies"].append({
        "id": len(data["movies"]) + 1,
        "title": title,
        "file_id": file_id,
        "genre": genre,
        "year": year
    })

    categorize_movie({
        "title": title,
        "genre": genre,
        "year": year
    })

    save_data(data)

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": CHANNEL,
        "video": file_id,
        "caption": f"🎬 {title}"
    })

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "callback_query" in update:
        data_cb = update["callback_query"]["data"]
        chat_id = update["callback_query"]["message"]["chat"]["id"]

        if data_cb == "home":
            show_home(chat_id)
        elif data_cb == "genres":
            show_movies(chat_id, list(data["categories"].keys()))
        elif data_cb.startswith("movie_"):
            show_movie_card(chat_id, data_cb.replace("movie_", ""))

        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message:
        if message["text"] == "/start":
            show_home(chat_id)

    elif "video" in message or "document" in message:
        handle_video(chat_id, message)

    return "ok"

@app.route("/")
def home():
    return "Bot läuft"

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=8080)