# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE)
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
# 🧠 STORY
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
Schreibe eine deutsche Filmbeschreibung.
- 3–5 Sätze
- konkret & realistisch
- keine Floskeln
"""
            }]
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 100:
            raise Exception()

        return text

    except:
        return (
            f"{title} beginnt mit einer Situation, die schnell außer Kontrolle gerät. "
            f"Ein zentraler Charakter gerät in ein brutales Umfeld aus Druck und Gewalt, "
            f"in dem jede Entscheidung weitreichende Konsequenzen hat. "
            f"Während sich die Lage zuspitzt, wird klar, dass größere Kräfte im Hintergrund wirken."
        )

# ================================
# ⭐ USER RATING (READY)
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

    user = avg_rating(m)
    views = m.get("views", 0)

    return imdb * 1.5 + user * 2 + views * 0.3

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
# 🎞 AUTO COLLECTIONS
# ================================

def build_auto_collections(data):
    collections = {
        "🔥 Beste Action": [],
        "🧠 Thriller": [],
        "😂 Comedy": [],
        "🚀 Sci-Fi": [],
        "👑 Top Filme": []
    }

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        genre = movie.get("Genre", "").lower()

        if "action" in genre:
            collections["🔥 Beste Action"].append(m)

        if "thriller" in genre or "crime" in genre:
            collections["🧠 Thriller"].append(m)

        if "comedy" in genre:
            collections["😂 Comedy"].append(m)

        if "sci-fi" in genre:
            collections["🚀 Sci-Fi"].append(m)

        try:
            if float(movie.get("imdbRating", 0)) >= 7.5:
                collections["👑 Top Filme"].append(m)
        except:
            pass

    return collections

# ================================
# 🌍 TRENDING VERGLEICH
# ================================

def get_channel_trending(data):
    return sorted(data["movies"], key=lambda x: x.get("views", 0), reverse=True)[:10]

def get_global_trending(data):
    scored = []

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        try:
            imdb = float(movie.get("imdbRating", 0))
        except:
            imdb = 0

        scored.append((imdb * 2, m))

    scored.sort(reverse=True)
    return [m for _, m in scored[:10]]

# ================================
# GRID
# ================================

def show_grid(chat_id, movies, page=0):
    SESSION[chat_id] = movies

    per_page = 3
    subset = movies[page*per_page:(page+1)*per_page]

    for m in subset:
        movie = get_movie(m["title"])
        if not movie:
            continue

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"],
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ Öffnen", "callback_data": f"movie_{movie['Title']}"}
                ]]
            }
        })

# ================================
# 🎬 FILM CARD (DEIN DESIGN)
# ================================

def send_card(chat_id, movie, local):
    title = movie.get("Title")
    year = movie.get("Year")

    genre = movie.get("Genre", "")
    genres = [g.strip() for g in genre.split(",")]
    main_genres = " • ".join(genres[:2])

    imdb = movie.get("imdbRating")
    runtime = movie.get("Runtime")
    director = movie.get("Director")

    plot = generate_story(title, movie.get("Plot"), genre)

    # 🔥 BADGES
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

    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": movie["Poster"]
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

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n\n🔥 Netflix UI Simulation"
    })

    rankings = get_rankings(data)

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🔥 Trending"})
    show_grid(chat_id, rankings["🔥 Trending"])

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🏆 Top"})
    show_grid(chat_id, rankings["🏆 Top"])

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🆕 Neu"})
    show_grid(chat_id, rankings["🆕 Neu"])

# ================================
# VIDEO (FORWARD READY)
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