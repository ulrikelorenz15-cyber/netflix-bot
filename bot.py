# ================================
# 🎬 NETFLIX BOT FINAL ULTIMATE V2
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
                "content": f"Schreibe eine kurze deutsche Netflix Filmbeschreibung (2-3 Sätze): {plot}"
            }]
        )

        return res.choices[0].message.content.strip()

    except:
        return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte, Druck und Konsequenzen."

# ================================
# REIHEN ERKENNUNG
# ================================

def detect_series(title):
    t = title.lower()

    if "fast" in t:
        return "Fast & Furious"
    if "harry potter" in t:
        return "Harry Potter"
    if "star wars" in t:
        return "Star Wars"
    if "bond" in t:
        return "James Bond"

    return None

# ================================
# COLLECTIONS ERKENNUNG
# ================================

def detect_collection(title):
    t = title.lower()

    if "marvel" in t or "avengers" in t:
        return "Marvel"
    if "dc" in t or "batman" in t:
        return "DC"
    if "jurassic" in t:
        return "Jurassic Park"
    if "rocky" in t:
        return "Rocky"

    return None

# ================================
# BANNER
# ================================

def create_banner(title):
    img = Image.new("RGB", (1280, 720), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0,0), title.upper(), font=font)
    x = (1280 - (bbox[2]-bbox[0]))//2
    y = (720 - (bbox[3]-bbox[1]))//2

    draw.text((x,y), title.upper(), fill="white", font=font)

    path = f"/tmp/{title}.jpg"
    img.save(path)
    return path

# ================================
# SORTIERUNG
# ================================

def categorize(data, title, genre):
    for g in genre.split(","):
        data["categories"].setdefault(g.strip(), []).append(title)

# ================================
# TRENDING
# ================================

def get_trending(data):
    return sorted(data["movies"], key=lambda x: x.get("views", 0), reverse=True)[:10]

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
        [{"text": "🔥 Trending", "callback_data": "trending"}],
        [{"text": "🆕 Neu", "callback_data": "new"}],
        [{"text": "🎬 Genres", "callback_data": "genres"}],
        [{"text": "🎞 Collections", "callback_data": "collections"}],
        [{"text": "🎬 Reihen", "callback_data": "series"}],
        [{"text": "🔤 A–Z", "callback_data": "az"}]
    ])

def show_genres(chat_id, data):
    buttons = [[{"text": g, "callback_data": f"genre_{g}"}] for g in data["categories"]]
    send_buttons(chat_id, "🎬 Genres", buttons)

def show_movies(chat_id, movies):
    buttons = [[{"text": m, "callback_data": f"movie_{m}"}] for m in movies]
    send_buttons(chat_id, "🎬 Filme", buttons)

def show_collections(chat_id, data):
    buttons = [[{"text": c, "callback_data": f"col_{c}"}] for c in data["collections"]]
    send_buttons(chat_id, "🎞 Collections", buttons)

def show_series(chat_id, data):
    buttons = [[{"text": s, "callback_data": f"series_{s}"}] for s in data["series"]]
    send_buttons(chat_id, "🎬 Reihen", buttons)

def show_az(chat_id):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    buttons = [[{"text": l, "callback_data": f"az_{l}"}] for l in alphabet]
    send_buttons(chat_id, "🔤 A–Z", buttons)

# ================================
# FILM CARD
# ================================

def send_film_card(chat_id, movie, file_id, movie_id):
    genre = movie["Genre"]
    genre_clean = " • ".join([g.strip() for g in genre.split(",")])
    actors = ", ".join(movie["Actors"].split(", ")[:3])

    plot = generate_story(movie["Title"], movie.get("Plot", ""), genre)

    caption = f"""🎬 {movie["Title"].upper()} ({movie["Year"]})
🔥 4K • {genre_clean}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]} • 🔞 FSK 16
🎥 {movie["Director"]}
🎭 {actors}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{movie_id}
━━━━━━━━━━━━━━
#{" #".join([g.strip() for g in genre.split(",")])}
@LibraryOfLegends"""

    if movie["Poster"] != "N/A":
        requests.post(f"{URL}/sendPhoto", json={"chat_id": chat_id, "photo": movie["Poster"]})
    else:
        path = create_banner(movie["Title"])
        with open(path, "rb") as img:
            requests.post(f"{URL}/sendPhoto", files={"photo": img}, data={"chat_id": chat_id})

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
    chat_id = message["chat"]["id"]
    title = message.get("caption", "Unknown")

    movie = get_movie(title)
    if not movie:
        send_message(chat_id, "❌ Film nicht gefunden")
        return

    movie_id = get_next_id(data)

    data["movies"].append({
        "id": movie_id,
        "title": movie["Title"],
        "file_id": video["file_id"],
        "genre": movie["Genre"],
        "views": 0
    })

    categorize(data, movie["Title"], movie["Genre"])

    # Collections
    col = detect_collection(movie["Title"])
    if col:
        data["collections"].setdefault(col, []).append(movie["Title"])

    # Serien
    ser = detect_series(movie["Title"])
    if ser:
        data["series"].setdefault(ser, []).append(movie["Title"])

    save_data(data)

    send_film_card(chat_id, movie, video["file_id"], movie_id)
    send_film_card(CHANNEL, movie, video["file_id"], movie_id)

# ================================
# SHOW MOVIE
# ================================

def show_movie(chat_id, title):
    data = load_data()
    m = next((x for x in data["movies"] if x["title"] == title), None)

    if not m:
        return

    movie = get_movie(title)
    if not movie:
        return

    m["views"] += 1
    save_data(data)

    send_film_card(chat_id, movie, m["file_id"], m["id"])

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

        if data_cb == "trending":
            show_movies(chat_id, [m["title"] for m in get_trending(data)])

        elif data_cb == "new":
            show_movies(chat_id, [m["title"] for m in list(reversed(data["movies"]))[:10]])

        elif data_cb == "genres":
            show_genres(chat_id, data)

        elif data_cb == "collections":
            show_collections(chat_id, data)

        elif data_cb == "series":
            show_series(chat_id, data)

        elif data_cb == "az":
            show_az(chat_id)

        elif data_cb.startswith("az_"):
            letter = data_cb.replace("az_", "")
            show_movies(chat_id, [m["title"] for m in data["movies"] if m["title"].startswith(letter)])

        elif data_cb.startswith("genre_"):
            show_movies(chat_id, data["categories"].get(data_cb.replace("genre_", ""), []))

        elif data_cb.startswith("col_"):
            show_movies(chat_id, data["collections"].get(data_cb.replace("col_", ""), []))

        elif data_cb.startswith("series_"):
            show_movies(chat_id, data["series"].get(data_cb.replace("series_", ""), []))

        elif data_cb.startswith("movie_"):
            show_movie(chat_id, data_cb.replace("movie_", ""))

        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    if "text" in message and message["text"] == "/start":
        show_home(message["chat"]["id"])

    elif "video" in message or "document" in message:
        handle_video(message)

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)