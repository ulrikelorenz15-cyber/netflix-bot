# ================================
# 🎬 NETFLIX BOT MASTER FINAL (FIXED)
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("OPENAI:", "OK" if OPENAI_API_KEY else "FEHLT ❌")

client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"
SESSION = {}

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

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
# 🧠 KI STORY (FIXED + DEBUG)
# ================================

def generate_story(title, plot, genre, user_id=None, series=None):
    try:
        print("🧠 KI START:", title)

        if not plot or plot == "N/A":
            plot = f"{title} ist ein Film aus dem Genre {genre}."

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine hochwertige deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

REGELN:
- 4 bis 5 Sätze
- konkret & realistisch
- KEINE Floskeln
- Netflix Stil
"""
            }],
            temperature=1.0
        )

        text = res.choices[0].message.content.strip()

        print("✅ KI TEXT:", text)

        if len(text) < 120:
            raise Exception("zu kurz")

        if any(w in text.lower() for w in ["the ", "after ", "when "]):
            raise Exception("englisch erkannt")

        return text

    except Exception as e:
        print("❌ KI ERROR:", e)

        return (
            f"{title} beginnt mit einer Situation, die schnell außer Kontrolle gerät. "
            f"Die Hauptfigur wird in ein gefährliches Umfeld gezogen, in dem jede Entscheidung Konsequenzen hat. "
            f"Während sich die Lage zuspitzt, treten immer größere Konflikte zutage. "
            f"Am Ende steht weit mehr auf dem Spiel als nur ein einzelnes Schicksal."
        )

# ================================
# KI REIHEN SYSTEM
# ================================

def detect_series_ai_full(title):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user","content": f"Film: {title}\nSERIE:\nORDER:\nPHASE:\nTIMELINE:"}],
            temperature=0.2
        )

        text = res.choices[0].message.content

        def get(key):
            if key in text:
                return text.split(key)[1].split("\n")[0].replace(":", "").strip()
            return None

        return {
            "series": get("SERIE"),
            "order": int(get("ORDER") or 0),
            "phase": get("PHASE"),
            "timeline": int(get("TIMELINE") or 0)
        }

    except:
        return {"series": None, "order": 0, "phase": None, "timeline": 0}

# ================================
# RATING
# ================================

def avg_rating(m):
    if not m.get("ratings"):
        return 0
    return round(sum(m["ratings"]) / len(m["ratings"]), 1)

# ================================
# FILM CARD (FINAL PRO MAX)
# ================================

def send_card(chat_id, movie, local):
    title = movie.get("Title", "Unknown")
    year = movie.get("Year", "2025")
    genre = movie.get("Genre", "Action")
    genre_clean = " • ".join([g.strip() for g in genre.split(",")])

    imdb = movie.get("imdbRating", "7.0")
    runtime = movie.get("Runtime", "120 Min")
    director = movie.get("Director", "-")

    actors = movie.get("Actors", "")
    actors = ", ".join(actors.split(", ")[:3]) if actors else "-"

    # 🔥 FIX: richtiger Aufruf
    plot = generate_story(
        title,
        movie.get("Plot"),
        genre,
        chat_id,
        local.get("series")
    )

    user_rating = avg_rating(local)

    series_text = ""
    if local.get("series"):
        series_text += f"\n📀 {local['series']}"
    if local.get("order"):
        series_text += f" • Teil {local['order']}"

    badge = ""
    if local.get("views", 0) >= 5:
        badge = "🔥 Trending\n"

    movie_id = local.get("id", "0000")

    tags = " ".join([f"#{g.strip().replace(' ', '')}" for g in genre.split(",")])
    tags += " #Neu"

    caption = f"""🎬 {title.upper()} ({year})
{badge}🔥 4K • {genre_clean}
━━━━━━━━━━━━━━
⭐ {imdb} • 👤 {user_rating} • ⏱ {runtime} • 🔞 FSK 16
🎥 {director}
🎭 {actors}
{series_text}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{movie_id}
━━━━━━━━━━━━━━
{tags}
@LibraryOfLegends"""

    # Poster
    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": movie["Poster"] if movie.get("Poster") != "N/A" else "https://via.placeholder.com/300x450"
    })

    # Video
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption
    })

# ================================
# VIDEO UPLOAD
# ================================

def handle_video(msg):
    data = load_data()

    video = msg.get("video") or msg.get("document")
    title = msg.get("caption")

    movie = get_movie(title)
    if not movie:
        return

    meta = detect_series_ai_full(movie["Title"])

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0,
        "ratings": [],
        **meta
    }

    data["movies"].append(entry)
    save_data(data)

    send_card(msg["chat"]["id"], movie, entry)
    send_card(CHANNEL, movie, entry)

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    collections = build_collections(data)

    send_message(chat_id, "🎬 Library of Legends\n\n🔥 Entdecke Filme wie auf Netflix")

    # 🔥 TRENDING ROW
    send_message(chat_id, "🔥 Trending")
    show_grid(chat_id, collections["🔥 Trending"], 0)

    # 🆕 NEW ROW
    send_message(chat_id, "🆕 Neu hinzugefügt")
    show_grid(chat_id, collections["🆕 Neu"], 0)

    # ⭐ TOP IMDb ROW
    top = [m for m in data["movies"] if float(get_movie(m["title"])["imdbRating"]) >= 7.5]
    send_message(chat_id, "⭐ Top IMDb")
    show_grid(chat_id, top, 0)

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
            title = cb.replace("movie_","")
            m = next(x for x in data["movies"] if x["title"] == title)
            movie = get_movie(title)
            m["views"] += 1
            save_data(data)
            send_card(chat_id, movie, m)

    msg = update.get("message")

    if msg and msg.get("text") == "/start":
        show_home(msg["chat"]["id"])

    if msg and ("video" in msg or "document" in msg):
        handle_video(msg)

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))