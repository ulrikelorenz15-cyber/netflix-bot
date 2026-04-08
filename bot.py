# ================================
# 🎬 NETFLIX BOT ULTIMATE FINAL V2
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
USER_STYLE = {}  # 🔥 Style pro User

# ================================
# DATA
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
# FILMREIHEN ERKENNUNG
# ================================

def detect_series(title):
    t = title.lower()

    if any(x in t for x in ["iron man", "avengers", "thor"]):
        return "marvel"
    if "fast" in t:
        return "fast"
    if "john wick" in t:
        return "wick"
    if "batman" in t:
        return "dc"

    return "default"

# ================================
# KI STORY SYSTEM (UPGRADE)
# ================================

def generate_story(title, plot, genre, user_id):
    try:
        style = USER_STYLE.get(user_id, "netflix")
        series = detect_series(title)

        series_map = {
            "marvel": "episch und heldenhaft",
            "fast": "rasant und familiär",
            "wick": "brutal und kompromisslos",
            "dc": "düster und komplex",
            "default": "realistisch"
        }

        style_map = {
            "netflix": "dramatisch und spannend",
            "prime": "klar und hochwertig",
            "dark": "sehr düster und intensiv"
        }

        prompt = f"""
Schreibe eine deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Serie Stil:
{series_map[series]}

Plattform Stil:
{style_map[style]}

Inhalt:
{plot}

Erstelle:
1. Kurzbeschreibung (1 Satz)
2. Lange Beschreibung (4-6 Sätze)

Nur Deutsch.

Format:
KURZ: ...
LANG: ...
"""

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1
        )

        text = res.choices[0].message.content.strip()

        short, long = "", ""

        if "KURZ:" in text and "LANG:" in text:
            short = text.split("KURZ:")[1].split("LANG:")[0].strip()
            long = text.split("LANG:")[1].strip()
        else:
            long = text

        # 🔥 fallback Deutsch
        if any(w in long.lower() for w in ["the ", "after ", "when "]):
            return "Ein intensiver Film voller Spannung.", "Ein Ermittler gerät in ein gefährliches Netz aus Gewalt und Intrigen."

        return short, long

    except Exception as e:
        print("❌ KI Fehler:", e)
        return "Ein intensiver Film.", "Keine Beschreibung verfügbar."

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
# BANNER FALLBACK
# ================================

def create_banner(title):
    img = Image.new("RGB", (1280, 720), (15, 15, 15))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    text = title.upper()
    bbox = draw.textbbox((0, 0), text, font=font)

    x = (1280 - (bbox[2]-bbox[0])) // 2
    y = (720 - (bbox[3]-bbox[1])) // 2

    draw.text((x, y), text, fill="white", font=font)

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

# ================================
# UI
# ================================

def send_buttons(chat_id, text, buttons):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons}
    })

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def show_home(chat_id):
    send_buttons(chat_id, "🎬 Library of Legends", [
        [{"text": "🎬 Genres", "callback_data": "genres"}],
        [{"text": "🧠 Style", "callback_data": "styles"}]
    ])

def show_styles(chat_id):
    send_buttons(chat_id, "🧠 Style wählen:", [
        [{"text": "🎬 Netflix", "callback_data": "style_netflix"}],
        [{"text": "🛒 Prime", "callback_data": "style_prime"}],
        [{"text": "🌑 Dark", "callback_data": "style_dark"}],
        [{"text": "🔙", "callback_data": "home"}]
    ])

def show_genres(chat_id, data):
    buttons = [[{"text": g, "callback_data": f"genre_{g}"}] for g in data["categories"]]
    buttons.append([{"text": "🔙", "callback_data": "home"}])
    send_buttons(chat_id, "🎬 Genres", buttons)

def show_movies(chat_id, movies):
    buttons = []

    for m in movies[:10]:
        buttons.append([{
            "text": f"🎬 {m}",
            "callback_data": f"movie_{m}"
        }])

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

    short, plot = generate_story(title, movie["Plot"], movie["Genre"], chat_id)

    caption = f"""🎬 {title.upper()} ({movie["Year"]})
🔥 {movie["Genre"]}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
🎭 {", ".join(movie["Actors"].split(", ")[:3])}
━━━━━━━━━━━━━━
🧠 {short}

📖 STORY
{plot}
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
# VIDEO UPLOAD (MIT CARD)
# ================================

def handle_video(message):
    data = load_data()

    video = message.get("video") or message.get("document")
    title = message.get("caption", "Unknown")

    movie = get_movie(title)
    if not movie:
        print("❌ Film nicht gefunden")
        return

    title = movie["Title"]
    genre = movie["Genre"]
    year = movie["Year"]

    short, plot = generate_story(title, movie["Plot"], genre, message["chat"]["id"])

    data["movies"].append({
        "title": title,
        "file_id": video["file_id"],
        "genre": genre,
        "year": year
    })

    categorize(data, title, genre, year)
    save_data(data)

    caption = f"""🎬 {title.upper()} ({year})
🔥 {genre}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
🎭 {", ".join(movie["Actors"].split(", ")[:3])}
━━━━━━━━━━━━━━
🧠 {short}

📖 STORY
{plot}
━━━━━━━━━━━━━━"""

    # Poster
    if movie["Poster"] != "N/A":
        requests.post(f"{URL}/sendPhoto", json={"chat_id": CHANNEL, "photo": movie["Poster"]})
    else:
        path = create_banner(title)
        with open(path, "rb") as img:
            requests.post(f"{URL}/sendPhoto", files={"photo": img}, data={"chat_id": CHANNEL})

    # Video + Card
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": CHANNEL,
        "video": video["file_id"],
        "caption": caption
    })

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

        elif data_cb == "genres":
            show_genres(chat_id, data)

        elif data_cb == "styles":
            show_styles(chat_id)

        elif data_cb.startswith("style_"):
            USER_STYLE[chat_id] = data_cb.replace("style_", "")
            send_message(chat_id, "✅ Style gespeichert")

        elif data_cb.startswith("genre_"):
            show_movies(chat_id, data["categories"].get(data_cb.replace("genre_", ""), []))

        elif data_cb.startswith("movie_"):
            show_movie(chat_id, data_cb.replace("movie_", ""))

        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message and message["text"] == "/start":
        show_home(chat_id)

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