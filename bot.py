# ================================
# 🎬 NETFLIX BOT FINAL (HYBRID STORY MODE)
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
# 🧠 HYBRID STORY MODE
# ================================

def generate_story(title, plot, genre):
    try:
        if not plot or plot == "N/A":
            raise Exception("kein plot")

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Schreibe eine deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

REGELN:
- 2 bis 3 Sätze
- konkret & direkt
- keine Floskeln
- Netflix Stil
"""
            }],
            temperature=1.0
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 80:
            raise Exception("zu kurz")

        if any(w in text.lower() for w in ["the ", "after ", "when "]):
            raise Exception("englisch")

        return text

    except:
        return (
            f"{title} beginnt mit einer Situation, die schnell außer Kontrolle gerät. "
            f"Ein erfahrener Protagonist gerät in ein brutales Umfeld aus Gewalt und Druck, "
            f"in dem jede Entscheidung Konsequenzen hat. Während sich die Ereignisse zuspitzen, "
            f"gerät er zunehmend ins Visier mächtiger Gegner."
        )

# ================================
# COLLECTIONS
# ================================

def build_collections(data):
    return {
        "🔥 Trending": sorted(data["movies"], key=lambda x: x.get("views", 0), reverse=True),
        "🆕 Neu": list(reversed(data["movies"]))
    }

# ================================
# ⭐ EMPFEHLUNGSSYSTEM
# ================================

def get_recommendations(data, base_movie):
    base = get_movie(base_movie["title"])
    if not base:
        return []

    base_genre = base.get("Genre", "").lower()
    scored = []

    for m in data["movies"]:
        if m["title"] == base_movie["title"]:
            continue

        movie = get_movie(m["title"])
        if not movie:
            continue

        score = 0

        if any(g.strip().lower() in base_genre for g in movie.get("Genre", "").split(",")):
            score += 2

        try:
            score += float(movie.get("imdbRating", 0)) / 5
        except:
            pass

        score += m.get("views", 0) * 0.2

        scored.append((score, m))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in scored[:5]]

# ================================
# GRID
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

    if nav:
        requests.post(f"{URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "Navigation",
            "reply_markup": {"inline_keyboard": [nav]}
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

    tags = f"#{genres[0]} #{genres[1] if len(genres)>1 else genres[0]} #Neu"

    caption = f"""🎬 {title.upper()} ({year})
🔥 4K • {main_genres}
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

    # ⭐ Empfehlungen
    data = load_data()
    recs = get_recommendations(data, local)

    if recs:
        requests.post(f"{URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": "🎯 Das könnte dir auch gefallen:"
        })

        for r in recs[:3]:
            movie_r = get_movie(r["title"])
            if not movie_r:
                continue

            requests.post(f"{URL}/sendPhoto", json={
                "chat_id": chat_id,
                "photo": movie_r["Poster"],
                "caption": movie_r["Title"],
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "▶️ Öffnen", "callback_data": f"movie_{movie_r['Title']}"}
                    ]]
                }
            })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    collections = build_collections(data)

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n\n🔥 Entdecke Filme wie auf Netflix"
    })

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🔥 Trending"})
    show_grid(chat_id, collections["🔥 Trending"], 0)

    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": "🆕 Neu"})
    show_grid(chat_id, collections["🆕 Neu"], 0)

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

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0
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

        elif cb.startswith("grid_"):
            page = int(cb.split("_")[1])
            show_grid(chat_id, SESSION.get(chat_id, []), page)

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