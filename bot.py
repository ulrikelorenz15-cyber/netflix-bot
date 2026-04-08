# ================================
# 🎬 ULTIMATE TELEGRAM NETFLIX BOT
# ================================

import os
import json
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ================================
# CONFIG
# ================================

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
OMDB_KEY = "a3776f86"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"

# ================================
# DATA SYSTEM
# ================================

def load_data():
    default = {
        "movies": [],
        "categories": {},
        "years": {}
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
# KI STORY
# ================================

def generate_story(title, plot, genre):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine realistische deutsche Netflix Beschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

4-6 Sätze, direkt, spannend, keine Floskeln.
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

def get_movie(title):
    try:
        r = requests.get(f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full").json()
        if r.get("Response") == "False":
            return None
        return r
    except:
        return None

# ================================
# BANNER (Fallback)
# ================================

def create_banner(title):
    img = Image.new("RGB", (1280, 720), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    text = title.upper()

    bbox = draw.textbbox((0,0), text, font=font)
    x = (1280 - (bbox[2]-bbox[0]))//2
    y = (720 - (bbox[3]-bbox[1]))//2

    draw.text((x,y), text, fill="white", font=font)

    path = f"/tmp/{title}.jpg"
    img.save(path)
    return path

# ================================
# SORTIERUNG
# ================================

def categorize(data, title, genre, year):
    for g in genre.split(","):
        g = g.strip()
        data["categories"].setdefault(g, []).append(title)

    y = int(year) if year.isdigit() else 2025
    group = "2020+" if y >= 2020 else "2010+"
    data["years"].setdefault(group, []).append(title)

# ================================
# UI
# ================================

def send_buttons(chat_id, text, buttons):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons}
    })

def home(chat_id):
    send_buttons(chat_id, "🎬 Library of Legends", [
        [{"text": "🎬 Genres", "callback_data": "genres"}],
        [{"text": "📅 Jahre", "callback_data": "years"}]
    ])

def show_genres(chat_id, data):
    buttons = [[{"text": g, "callback_data": f"genre_{g}"}] for g in data["categories"]]
    buttons.append([{"text": "🔙", "callback_data": "home"}])
    send_buttons(chat_id, "🎬 Genres", buttons)

def show_movies(chat_id, movies):
    buttons = [[{"text": m, "callback_data": f"movie_{m}"}] for m in movies[:10]]
    buttons.append([{"text": "🔙", "callback_data": "home"}])
    send_buttons(chat_id, "🎬 Filme", buttons)

# ================================
# FILM CARD
# ================================

def show_movie(chat_id, title):
    data = load_data()
    local = next((m for m in data["movies"] if m["title"] == title), None)
    if not local:
        return

    movie = get_movie(title)
    if not movie:
        return

    plot = generate_story(title, movie["Plot"], movie["Genre"])

    caption = f"""🎬 {title.upper()} ({movie["Year"]})
🔥 {movie["Genre"]}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
🎭 {", ".join(movie["Actors"].split(", ")[:3])}
━━━━━━━━━━━━━━
📖 {plot}
━━━━━━━━━━━━━━"""

    if movie["Poster"] != "N/A":
        requests.post(f"{URL}/sendPhoto", json={"chat_id": chat_id, "photo": movie["Poster"]})
    else:
        path = create_banner(title)
        with open(path, "rb") as img:
            requests.post(f"{URL}/sendPhoto", files={"photo": img}, data={"chat_id": chat_id})

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": local["file_id"],
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

    data["movies"].append({
        "title": movie["Title"],
        "file_id": video["file_id"],
        "genre": movie["Genre"],
        "year": movie["Year"]
    })

    categorize(data, movie["Title"], movie["Genre"], movie["Year"])
    save_data(data)

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
            home(chat_id)

        elif data_cb == "genres":
            show_genres(chat_id, data)

        elif data_cb.startswith("genre_"):
            g = data_cb.replace("genre_", "")
            show_movies(chat_id, data["categories"].get(g, []))

        elif data_cb.startswith("movie_"):
            show_movie(chat_id, data_cb.replace("movie_", ""))

        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message and message["text"] == "/start":
        home(chat_id)

    elif "video" in message or "document" in message:
        handle_video(message)

    return "ok"

@app.route("/")
def home_route():
    return "Bot läuft 🚀"

# ================================
# START
# ================================

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)