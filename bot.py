# ================================
# 🎬 TELEGRAM BOT (KI FINAL STABLE)
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
print("OPENAI KEY:", "OK" if OPENAI_API_KEY else "FEHLT ❌")

# 🔥 FIX: CLIENT DEFINIERT
client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

data = load_data()

# ================================
# KI STORY
# ================================

def generate_story(title, plot):
    try:
        if not OPENAI_API_KEY:
            print("❌ Kein OpenAI Key")
            return "Ein intensiver Film voller Spannung und unerwarteter Wendungen."

        print("🎬 Sende an KI:", title)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine hochwertige deutsche Film-Beschreibung im Netflix Stil.

Film: {title}

Inhalt:
{plot}

Maximal 3-4 Sätze. Natürliches Deutsch.
"""
            }]
        )

        text = response.choices[0].message.content.strip()

        print("✅ KI Story generiert")

        return text

    except Exception as e:
        print("❌ KI ERROR:", e)
        return "Ein spannender Film mit intensiven Momenten und überraschenden Wendungen."

# ================================
# SEND MESSAGE
# ================================

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

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
# REIHEN
# ================================

def detect_series(title):
    t = title.lower()

    if any(x in t for x in ["iron man", "avengers", "thor"]):
        return "🔥 Marvel"

    if "fast" in t:
        return "🚗 Fast & Furious"

    if "star wars" in t:
        return "🌌 Star Wars"

    if "harry potter" in t:
        return "🧙 Harry Potter"

    if "john wick" in t:
        return "🔫 John Wick"

    return ""

# ================================
# HASHTAGS
# ================================

def build_hashtags(genre):
    tags = genre.split(",")
    return " ".join([f"#{g.strip().replace(' ', '')}" for g in tags])

# ================================
# BANNER
# ================================

def create_banner(title):
    safe_title = title.replace("/", "").replace("\\", "").replace(":", "")

    img = Image.new("RGB", (1280, 720), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    text = safe_title.upper()

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    x = (1280 - w) // 2
    y = (720 - h) // 2

    draw.text((x, y), text, fill="white", font=font)

    path = f"/tmp/{safe_title}.jpg"
    img.save(path)

    return path

# ================================
# START
# ================================

def handle_start(chat_id):
    send_message(chat_id, "🎬 Library of Legends\n\nSchick mir ein Video!")

# ================================
# SEARCH (🔥 FIX FEHLTE!)
# ================================

def handle_text(chat_id, text):
    results = [m for m in data["movies"] if text.lower() in m["title"].lower()]

    if not results:
        send_message(chat_id, "❌ Kein Film gefunden")
        return

    msg = "🎬 Ergebnisse:\n\n"

    for m in results[:10]:
        msg += f"🎬 {m['title']} ({m.get('year','?')})\n"

    send_message(chat_id, msg)

# ================================
# VIDEO
# ================================

def handle_video(chat_id, message):
    video = message.get("video") or message.get("document")
    title = message.get("caption", "Unknown")

    file_id = video["file_id"]

    movie = get_movie_data(title)

    if movie:
        title = movie.get("Title", title)
        year = movie.get("Year", "2025")
        genre = movie.get("Genre", "Action")
        rating = movie.get("imdbRating", "7.0")
        runtime = movie.get("Runtime", "120 min")
        director = movie.get("Director", "-")

        original_plot = movie.get("Plot", "")
        plot = generate_story(title, original_plot)
    else:
        year = "2025"
        genre = "Action"
        rating = "7.0"
        runtime = "120 min"
        director = "-"
        plot = "Ein spannender Film voller Action und unerwarteter Wendungen."

    series = detect_series(title)
    hashtags = build_hashtags(genre)

    new_id = len(data["movies"]) + 1

    caption = f"""🎬 {title.upper()} ({year})
🔥 4K • {genre}
━━━━━━━━━━━━━━
⭐ {rating} • ⏱ {runtime} • 🔞 FSK 16
🎥 {director}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{str(new_id).zfill(4)}
━━━━━━━━━━━━━━
{hashtags}
{series}
@LibraryOfLegends"""

    data["movies"].append({
        "id": new_id,
        "title": title,
        "file_id": file_id,
        "genre": genre,
        "year": year
    })

    save_data(data)

    banner = create_banner(title)
    with open(banner, "rb") as img:
        requests.post(f"{URL}/sendPhoto", files={"photo": img}, data={"chat_id": CHANNEL})

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": CHANNEL,
        "video": file_id,
        "caption": caption
    })

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message:
        if message["text"] == "/start":
            handle_start(chat_id)
        else:
            handle_text(chat_id, message["text"])

    elif "video" in message or "document" in message:
        handle_video(chat_id, message)

    return "ok"

@app.route("/")
def home():
    return "🤖 Bot läuft!"

# ================================
# START
# ================================

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=8080)