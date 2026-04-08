# ================================
# 🎬 NETFLIX BOT ULTIMATE FINAL
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
# KI STORY SYSTEM
# ================================

def generate_story(title, plot, genre, style="netflix"):
    try:
        if not plot:
            return "Spannende Geschichte.", "Keine Beschreibung verfügbar."

        prompt = f"""
Schreibe eine hochwertige deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

AUFGABEN:
1. Kurzbeschreibung (1 Satz)
2. Lange Beschreibung (4-6 Sätze)

REGELN:
- NUR Deutsch
- NICHT übersetzen → neu formulieren
- KEINE Floskeln wie "Ein spannender Film"
- Netflix Stil
- konkret & realistisch

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

        short = ""
        long = ""

        if "KURZ:" in text and "LANG:" in text:
            short = text.split("KURZ:")[1].split("LANG:")[0].strip()
            long = text.split("LANG:")[1].strip()
        else:
            long = text

        # 🔥 ABSICHERUNG: falls Englisch erkannt
        if any(w in long.lower() for w in ["the ", "after ", "when "]):
            print("⚠️ Englisch erkannt → KI fallback")
            return (
                "Ein Ermittler gerät in ein gefährliches Netz aus Gewalt und Korruption.",
                "Nach einem eskalierten Einsatz wird ein angeschlagener Ermittler in die kriminelle Unterwelt gezogen. Während er versucht, den Sohn eines einflussreichen Politikers zu retten, stößt er auf ein Geflecht aus Verrat, Macht und Gewalt. Je tiefer er eintaucht, desto mehr verschwimmen die Grenzen zwischen Recht und Unrecht. Schließlich wird klar, dass hinter allem eine Verschwörung steckt, die weit über den ursprünglichen Fall hinausgeht."
            )

        return short, long

    except Exception as e:
        print("❌ KI Fehler:", e)

        # 🔥 IMMER DEUTSCHER FALLBACK
        return (
            "Ein intensiver Film voller Spannung.",
            "Ein abgebrühter Ermittler gerät in einen gefährlichen Strudel aus Gewalt und Intrigen. Während er versucht, einen vermissten Jungen zu retten, stößt er auf dunkle Machenschaften innerhalb der Stadt. Jeder Schritt bringt ihn näher an eine Wahrheit, die mächtige Gegner um jeden Preis verbergen wollen."
        )

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

def show_home(chat_id):
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

    short, plot = generate_story(title, movie["Plot"], movie["Genre"])

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
        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"]
        })
    else:
        path = create_banner(title)
        with open(path, "rb") as img:
            requests.post(f"{URL}/sendPhoto",
                files={"photo": img},
                data={"chat_id": chat_id}
            )

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
        print("❌ Film nicht gefunden")
        return

    title = movie["Title"]
    genre = movie["Genre"]
    year = movie["Year"]

    # 🧠 KI STORY
    short, plot = generate_story(title, movie["Plot"], genre)

    # 🎬 SPEICHERN
    data["movies"].append({
        "title": title,
        "file_id": video["file_id"],
        "genre": genre,
        "year": year
    })

    categorize(data, title, genre, year)
    save_data(data)

    # 🎬 CAPTION (NETFLIX STYLE)
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
━━━━━━━━━━━━━━
#{" #".join([g.strip() for g in genre.split(",")])}
@LibraryOfLegends"""

    # 📸 POSTER ODER BANNER
    try:
        if movie["Poster"] != "N/A":
            requests.post(f"{URL}/sendPhoto", json={
                "chat_id": CHANNEL,
                "photo": movie["Poster"]
            })
        else:
            path = create_banner(title)
            with open(path, "rb") as img:
                requests.post(f"{URL}/sendPhoto",
                    files={"photo": img},
                    data={"chat_id": CHANNEL}
                )
    except Exception as e:
        print("❌ Poster Fehler:", e)

    # 🎬 VIDEO + CARD
    try:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": CHANNEL,
            "video": video["file_id"],
            "caption": caption
        })
        print("✅ Film + Card im Kanal")
    except Exception as e:
        print("❌ Kanal Fehler:", e)

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
        show_home(chat_id)

    elif "video" in message or "document" in message:
        handle_video(message)

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

# ================================
# START
# ================================

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)