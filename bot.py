# ================================
# 🎬 NETFLIX BOT FINAL BOSS MODE (STABLE GOD VERSION)
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
            return json.load(open(DATA_FILE))
        except:
            pass
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
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Schreibe eine kurze deutsche Netflix Filmbeschreibung (2-3 Sätze, konkret): {plot}"
            }]
        )
        text = res.choices[0].message.content.strip()
        if len(text) < 40:
            raise Exception()
        return text
    except:
        return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte und Konsequenzen."

# ================================
# 📊 RANKING SYSTEM
# ================================

def calculate_score(movie):
    rating = movie.get("rating", 0)
    views = movie.get("views", 0)
    freshness = int(movie.get("id", 0))
    return (rating * 2) + (views * 0.5) + (freshness * 0.1)

def get_trending(data):
    enriched = []

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        try:
            m["rating"] = float(movie.get("imdbRating", "0"))
        except:
            m["rating"] = 0

        m["score"] = calculate_score(m)
        enriched.append(m)

    return sorted(enriched, key=lambda x: x["score"], reverse=True)

# ================================
# 🎞 MARVEL TIMELINE
# ================================

MARVEL = [
    "Iron Man", "Iron Man 2", "Thor",
    "Captain America", "Avengers",
    "Guardians of the Galaxy",
    "Doctor Strange",
    "Black Panther",
    "Avengers: Infinity War",
    "Avengers: Endgame"
]

def get_marvel(data):
    result = []
    for name in MARVEL:
        for m in data["movies"]:
            if name.lower() in m["title"].lower():
                result.append(m)
    return result

# ================================
# 🎞 AUTO COLLECTIONS
# ================================

def build_collections(data):
    result = {
        "🔥 Trending": get_trending(data),
        "🆕 Neu": list(reversed(data["movies"])),
        "⭐ Top IMDb": [],
        "🔥 Action": [],
        "🚀 Sci-Fi": []
    }

    for m in data["movies"]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        genre = movie.get("Genre", "").lower()

        try:
            rating = float(movie.get("imdbRating", "0"))
        except:
            rating = 0

        if rating >= 7.5:
            result["⭐ Top IMDb"].append(m)

        if "action" in genre:
            result["🔥 Action"].append(m)

        if "sci-fi" in genre:
            result["🚀 Sci-Fi"].append(m)

    return result

# ================================
# 🎬 GRID (POSTER SWIPE)
# ================================

def show_grid(chat_id, movies, page=0):
    SESSION[chat_id] = movies

    per_page = 3
    start = page * per_page
    end = start + per_page

    for m in movies[start:end]:
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

    nav = []

    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"grid_{page-1}"})

    if end < len(movies):
        nav.append({"text": "➡️", "callback_data": f"grid_{page+1}"})

    buttons = [nav] if nav else []
    buttons.append([{"text": "🏠 Home", "callback_data": "home"}])

    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Browse",
        "reply_markup": {"inline_keyboard": buttons}
    })

# ================================
# 🎬 FILM CARD
# ================================

def send_film_card(chat_id, movie, file_id, movie_id):
    plot = generate_story(movie["Title"], movie.get("Plot", ""), movie["Genre"])

    caption = f"""🎬 {movie["Title"].upper()} ({movie["Year"]})
🔥 {movie["Genre"]}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{movie_id}
━━━━━━━━━━━━━━"""

    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": movie["Poster"]
    })

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
    title = message.get("caption", "Unknown")

    movie = get_movie(title)
    if not movie:
        return

    movie_id = get_next_id(data)

    entry = {
        "id": movie_id,
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)

    chat_id = message["chat"]["id"]

    send_film_card(chat_id, movie, video["file_id"], movie_id)
    send_film_card(CHANNEL, movie, video["file_id"], movie_id)

# ================================
# UI
# ================================

def show_home(chat_id):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": "🎬 Library of Legends",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🔥 Trending", "callback_data": "trending"}],
                [{"text": "🆕 Neu", "callback_data": "new"}],
                [{"text": "⭐ Top IMDb", "callback_data": "top"}],
                [{"text": "🎞 Marvel", "callback_data": "marvel"}],
                [{"text": "🎞 Collections", "callback_data": "collections"}]
            ]
        }
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

        collections = build_collections(data)

        if data_cb == "home":
            show_home(chat_id)

        elif data_cb == "trending":
            show_grid(chat_id, collections["🔥 Trending"])

        elif data_cb == "new":
            show_grid(chat_id, collections["🆕 Neu"])

        elif data_cb == "top":
            show_grid(chat_id, collections["⭐ Top IMDb"])

        elif data_cb == "marvel":
            show_grid(chat_id, get_marvel(data))

        elif data_cb == "collections":
            show_grid(chat_id, collections["🔥 Action"])

        elif data_cb.startswith("movie_"):
            title = data_cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                movie = get_movie(title)
                m["views"] += 1
                save_data(data)
                send_film_card(chat_id, movie, m["file_id"], m["id"])

        elif data_cb.startswith("grid_"):
            page = int(data_cb.split("_")[1])
            show_grid(chat_id, SESSION.get(chat_id, []), page)

        return "ok"

    message = update.get("message")

    if message and ("video" in message or "document" in message):
        handle_video(message)

    if message and message.get("text") == "/start":
        show_home(message["chat"]["id"])

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))