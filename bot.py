
# ================================
# 🎬 NETFLIX BOT FINAL BOSS MODE (REAL FINAL)
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
SESSION = {}  # 🔥 merkt sich aktuelle Grid Liste pro User

# ================================
# DATA
# ================================

def load_data():
    default = {"movies": []}
    if os.path.exists(DATA_FILE):
        try:
            data = json.load(open(DATA_FILE))
            if "movies" not in data:
                data["movies"] = []
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
# KI STORY (REALISTISCH)
# ================================

def generate_story(title, plot, genre):
    try:
        if not plot or plot == "N/A":
            return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte, Druck und Konsequenzen."

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine deutsche Netflix Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

REGELN:
- 2–3 Sätze
- konkret & realistisch
- keine Floskeln
"""
            }]
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 50:
            raise Exception()

        return text

    except:
        return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte, Druck und Konsequenzen, bei der jede Entscheidung neue Folgen hat."

# ================================
# AUTO COLLECTIONS
# ================================

def build_collections(data):
    result = {
        "🔥 Trending": sorted(data["movies"], key=lambda x: x.get("views", 0), reverse=True),
        "🆕 Neu": list(reversed(data["movies"])),
        "⭐ Top IMDb": []
    }

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        try:
            if float(movie["imdbRating"]) >= 7.5:
                result["⭐ Top IMDb"].append(m)
        except:
            pass

    return result

# ================================
# GRID (SWIPE)
# ================================

def show_grid(chat_id, movies, page=0):
    SESSION[chat_id] = movies

    per_page = 3
    start = page * per_page
    end = start + per_page

    subset = movies[start:end]

    for m in subset:
        movie = get_movie(m["title"])
        if not movie:
            continue

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"] if movie["Poster"] != "N/A" else "https://via.placeholder.com/300x450",
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
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

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Browse",
        "reply_markup": {"inline_keyboard": buttons}
    })

# ================================
# UI
# ================================

def show_home(chat_id):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🔥 Trending", "callback_data": "row_trending"}],
                [{"text": "🆕 Neu", "callback_data": "row_new"}],
                [{"text": "⭐ Top IMDb", "callback_data": "row_top"}]
            ]
        }
    })

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
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]} • 🔞 FSK 16
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
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)

    chat_id = message["chat"]["id"]

    send_film_card(chat_id, movie, video["file_id"], movie_id)
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

        collections = build_collections(data)

        if data_cb == "home":
            show_home(chat_id)

        elif data_cb == "row_trending":
            show_grid(chat_id, collections["🔥 Trending"])

        elif data_cb == "row_new":
            show_grid(chat_id, collections["🆕 Neu"])

        elif data_cb == "row_top":
            show_grid(chat_id, collections["⭐ Top IMDb"])

        elif data_cb.startswith("movie_"):
            title = data_cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                movie = get_movie(title)
                m["views"] += 1
                save_data(data)
                send_film_card(chat_id, movie, m["file_id"], m["id"])

        elif data_cb.startswith("grid_"):
            page = int(data_cb.split("_")[1])
            show_grid(chat_id, SESSION.get(chat_id, []), page)

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