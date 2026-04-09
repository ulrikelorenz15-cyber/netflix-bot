# ================================
# 🎬 NETFLIX BOT FINAL (FIXED)
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
SESSION = {}

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"movies": []}
    return {"movies": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

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
        r = requests.get(
            f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full",
            timeout=5
        ).json()

        if r.get("Response") == "False":
            return None

        return r
    except:
        return None

# ================================
# 🧠 STORY (VERBESSERT)
# ================================

def generate_story(title, plot, genre):
    try:
        if not plot or plot == "N/A":
            raise Exception()

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
- leicht düsterer Netflix Stil
- KEIN generischer Text
"""
            }],
            temperature=1.1
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 120:
            raise Exception()

        return text

    except:
        return (
            f"{title} beginnt mit einer scheinbar kontrollierten Situation, die schnell außer Kontrolle gerät. "
            f"Ein zentraler Charakter gerät in ein brutales Umfeld aus Druck und Gewalt, "
            f"in dem jede Entscheidung weitreichende Konsequenzen hat. "
            f"Mit jeder Entwicklung verschärfen sich die Konflikte und ziehen weitere Kreise. "
            f"Am Ende steht mehr auf dem Spiel als nur ein persönliches Schicksal."
        )

# ================================
# ⭐ USER RATING
# ================================

def avg_rating(m):
    if not m.get("ratings"):
        return 0
    return round(sum(m["ratings"]) / len(m["ratings"]), 1)

# ================================
# 📊 SCORE SYSTEM
# ================================

def get_score(m):
    try:
        movie = get_movie(m["title"])
        imdb = float(movie.get("imdbRating", 0))
    except:
        imdb = 0

    return imdb * 1.5 + avg_rating(m) * 2 + m.get("views", 0) * 0.3

# ================================
# 📊 RANKINGS
# ================================

def get_rankings(data):
    movies = data["movies"]

    return {
        "🔥 Trending": sorted(movies, key=lambda x: x.get("views", 0), reverse=True)[:10],
        "🏆 Top": sorted(movies, key=get_score, reverse=True)[:10],
        "🆕 Neu": list(reversed(movies))[:10]
    }

# ================================
# GRID
# ================================

def show_grid(chat_id, movies):
    SESSION[chat_id] = movies

    for m in movies[:3]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        poster = movie.get("Poster")
        if not poster or poster == "N/A":
            poster = "https://via.placeholder.com/300x450"

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": poster,
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ Öffnen", "callback_data": f"movie_{movie['Title']}"}
                ]]
            }
        })

# ================================
# 🎬 FILM CARD
# ================================

def send_card(chat_id, movie, local):
    title = movie.get("Title")
    year = movie.get("Year")

    genres = [g.strip() for g in movie.get("Genre", "").split(",")]
    main_genres = " • ".join(genres[:2])

    imdb = movie.get("imdbRating")
    runtime = movie.get("Runtime")
    director = movie.get("Director")

    plot = generate_story(title, movie.get("Plot"), movie.get("Genre"))

    # BADGES
    badge = ""
    if local.get("views", 0) >= 5:
        badge += "🔥 Trending\n"

    try:
        if float(imdb) >= 8:
            badge += "🌍 Global Top\n"
    except:
        pass

    tags = f"#{genres[0]} #{genres[1] if len(genres)>1 else genres[0]} #Neu"

    caption = f"""🎬 {title.upper()} ({year})
{badge}🔥 4K • {main_genres}
━━━━━━━━━━━━━━
⭐ {imdb} • ⏱ {runtime} • 🔞 FSK 16
🎥 {director}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{local.get("id")}
━━━━━━━━━━━━━━
{tags}
@LibraryOfLegends"""

    poster = movie.get("Poster")
    if not poster or poster == "N/A":
        poster = "https://via.placeholder.com/300x450"

    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": poster
    })

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    rankings = get_rankings(data)

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n\n🔥 Netflix UI Simulation"
    })

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🔥 Trending"})
    show_grid(chat_id, rankings["🔥 Trending"])

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🏆 Top"})
    show_grid(chat_id, rankings["🏆 Top"])

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🆕 Neu"})
    show_grid(chat_id, rankings["🆕 Neu"])

# ================================
# VIDEO
# ================================

def handle_video(msg):
    data = load_data()

    video = msg.get("video") or msg.get("document")
    title = msg.get("caption")

    movie = get_movie(title)
    if not movie:
        return

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0,
        "ratings": []
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

            if not m:
                return "ok"

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