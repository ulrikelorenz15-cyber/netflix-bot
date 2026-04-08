# ================================
# 🎬 NETFLIX BOT MASTER FINAL
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
# KI STORY
# ================================

def generate_story(title, plot, genre):
    try:
        # 🔥 Fallback wenn kein Plot
        if not plot or plot == "N/A":
            return f"{title} erzählt eine intensive Geschichte innerhalb des Genres {genre}, in der Konflikte, Entscheidungen und Konsequenzen im Mittelpunkt stehen."

        prompt = f"""
Schreibe eine hochwertige deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

REGELN:
- 4 bis 5 Sätze
- KEINE Floskeln wie "ein spannender Film"
- konkret beschreiben, was passiert
- Namen wie "ein Ermittler", "ein Soldat" etc. benutzen
- leicht düsterer Netflix Stil
- realistisch, nicht generisch
- KEINE Übersetzung → neu formulieren

Nur die Beschreibung.
"""

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1
        )

        text = res.choices[0].message.content.strip()

        # 🔥 Sicherheitscheck (zu kurz → neu)
        if len(text) < 120:
            raise Exception("zu kurz")

        # 🔥 Englisch-Filter
        if any(w in text.lower() for w in ["the ", "after ", "when ", "must "]):
            raise Exception("englisch erkannt")

        return text

    except:
        # 🔥 STARKER FALLBACK (kein Müll mehr)
        return (
            f"{title} beginnt mit einer scheinbar kontrollierten Situation, die schnell außer Kontrolle gerät. "
            f"Ein zentraler Charakter sieht sich gezwungen, sich durch ein immer gefährlicher werdendes Umfeld zu bewegen, "
            f"in dem Gewalt, Druck und Entscheidungen eng miteinander verknüpft sind. "
            f"Mit jeder Entwicklung verschärfen sich die Konflikte und ziehen weitere Kreise. "
            f"Am Ende steht nicht nur ein persönliches Schicksal auf dem Spiel, sondern weit mehr."
        )

# ================================
# KI REIHEN SYSTEM
# ================================

def detect_series_ai_full(title):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Film: {title}

Gib zurück:
SERIE:
ORDER:
PHASE:
TIMELINE:
"""
            }],
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
# SORTING
# ================================

def sort_series(movies):
    return sorted(movies, key=lambda x: x.get("order", 0))

def sort_timeline(movies):
    return sorted(movies, key=lambda x: x.get("timeline", 0))

# ================================
# RATING
# ================================

def avg_rating(m):
    if not m.get("ratings"):
        return 0
    return round(sum(m["ratings"]) / len(m["ratings"]), 1)

# ================================
# COLLECTIONS
# ================================

def build_collections(data):
    return {
        "🔥 Trending": sorted(data["movies"], key=lambda x: x["views"], reverse=True),
        "🆕 Neu": list(reversed(data["movies"]))
    }

# ================================
# GRID
# ================================

def show_grid(chat_id, movies, page=0):
    SESSION[chat_id] = movies

    per = 3
    subset = movies[page*per:(page+1)*per]

    for m in subset:
        movie = get_movie(m["title"])
        if not movie:
            continue

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"],
            "caption": f"{movie['Title']} ⭐ {movie['imdbRating']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️ Öffnen", "callback_data": f"movie_{movie['Title']}"}
                ]]
            }
        })

# ================================
# FILM CARD
# ================================

def send_card(chat_id, movie, local):
    # -------------------------------
    # BASIC DATA
    # -------------------------------
    title = movie.get("Title", "Unknown")
    year = movie.get("Year", "2025")
    genre = movie.get("Genre", "Action")
    genre_clean = " • ".join([g.strip() for g in genre.split(",")])

    imdb = movie.get("imdbRating", "7.0")
    runtime = movie.get("Runtime", "120 Min")
    director = movie.get("Director", "-")

    # 🎭 Schauspieler
    actors = movie.get("Actors", "")
    actors = ", ".join(actors.split(", ")[:3]) if actors else "-"

    # -------------------------------
    # KI STORY (BESSER)
    # -------------------------------
    plot = generate_story(title, movie.get("Plot"), genre)

    # -------------------------------
    # RATINGS
    # -------------------------------
    def avg_rating(m):
        if not m.get("ratings"):
            return 0
        return round(sum(m["ratings"]) / len(m["ratings"]), 1)

    user_rating = avg_rating(local)

    # -------------------------------
    # SERIES INFO
    # -------------------------------
    series = local.get("series")
    order = local.get("order")

    series_text = ""
    if series:
        series_text += f"\n📀 {series}"
    if order:
        series_text += f" • Teil {order}"

    # -------------------------------
    # TRENDING BADGE
    # -------------------------------
    badge = ""
    if local.get("views", 0) >= 5:
        badge = "🔥 Trending\n"

    # -------------------------------
    # FILM ID
    # -------------------------------
    movie_id = local.get("id", "0000")

    # -------------------------------
    # HASHTAGS
    # -------------------------------
    tags = " ".join([f"#{g.strip().replace(' ', '')}" for g in genre.split(",")])
    tags += " #Neu"

    # -------------------------------
    # FINAL CAPTION (PRO MAX DESIGN)
    # -------------------------------
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

    # -------------------------------
    # POSTER
    # -------------------------------
    if movie.get("Poster") and movie["Poster"] != "N/A":
        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie["Poster"]
        })
    else:
        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": "https://via.placeholder.com/300x450"
        })

    # -------------------------------
    # VIDEO + BUTTONS
    # -------------------------------
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "⭐1", "callback_data": f"rate_{movie_id}_1"},
                    {"text": "⭐2", "callback_data": f"rate_{movie_id}_2"},
                    {"text": "⭐3", "callback_data": f"rate_{movie_id}_3"}
                ],
                [
                    {"text": "⭐4", "callback_data": f"rate_{movie_id}_4"},
                    {"text": "⭐5", "callback_data": f"rate_{movie_id}_5"}
                ]
            ]
        }
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

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends"
    })

    show_grid(chat_id, collections["🔥 Trending"])
    show_grid(chat_id, collections["🆕 Neu"])

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

        elif cb.startswith("rate_"):
            _, mid, val = cb.split("_")
            for m in data["movies"]:
                if m["id"] == mid:
                    m["ratings"].append(int(val))
            save_data(data)

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