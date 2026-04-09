# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE SERIES BUILD)
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
CACHE = {}

# ================================
# UTILS
# ================================

def log_error(e):
    print("ERROR:", str(e))

def clean_title(raw):
    if not raw:
        return ""

    raw = raw.replace(".", " ")

    blacklist = ["1080p","720p","bluray","x264","x265","dvdrip","webdl"]
    words = raw.split()

    cleaned = [w for w in words if w.lower() not in blacklist]

    return " ".join(cleaned)

# ================================
# 🎞 AUTO SERIES SYSTEM
# ================================

SERIES_DB = {
    "Bourne": [
        "Identität",
        "Verschwörung",
        "Ultimatum",
        "Vermächtnis",
        "Jason Bourne"
    ],
    "Jurassic Park": [
        "Jurassic Park",
        "Vergessene Welt",
        "Jurassic Park 3",
        "Jurassic World",
        "gefallene Königreich",
        "neues Zeitalter"
    ]
}

MARVEL_PHASES = {
    "Phase 1": ["Iron Man","Hulk","Thor","Captain America","Avengers"],
    "Phase 2": ["Iron Man 3","Thor 2","Captain America 2","Guardians","Avengers 2"],
    "Phase 3": ["Civil War","Doctor Strange","Black Panther","Infinity War","Endgame"]
}

def detect_series(title):
    t = title.lower()

    for name, movies in SERIES_DB.items():
        for i, m in enumerate(movies):
            if m.lower() in t:
                return {"series": name, "order": i+1, "phase": None}

    for phase, movies in MARVEL_PHASES.items():
        for i, m in enumerate(movies):
            if m.lower() in t:
                return {"series": "Marvel", "order": i+1, "phase": phase}

    return {"series": None, "order": 0, "phase": None}

def get_series_list(data, name):
    items = [m for m in data["movies"] if m.get("series") == name]
    return sorted(items, key=lambda x: x.get("order", 0))

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return json.load(open(DATA_FILE))
        except:
            return {"movies": []}
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

# ================================
# OMDb CACHE
# ================================

def get_movie(title):
    if title in CACHE:
        return CACHE[title]

    try:
        r = requests.get(
            f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full",
            timeout=5
        ).json()

        if r.get("Response") == "False":
            return None

        CACHE[title] = r
        return r

    except Exception as e:
        log_error(e)
        return None

# ================================
# STORY
# ================================

def generate_story(title, plot, genre):
    try:
        if not plot or plot == "N/A":
            raise Exception()

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":f"""
Film: {title}
Genre: {genre}
Inhalt:
{plot}

4-5 Sätze, konkret, düster, Netflix Stil
"""}],
            temperature=1.1
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 120:
            raise Exception()

        return text

    except:
        return (
            f"{title} beginnt mit einer scheinbar kontrollierten Situation, die eskaliert. "
            f"Ein Charakter gerät in ein brutales Umfeld voller Druck und Gewalt. "
            f"Mit jeder Entscheidung verschärft sich die Lage weiter. "
            f"Am Ende steht mehr auf dem Spiel als nur ein persönliches Schicksal."
        )

# ================================
# RATING
# ================================

def avg_rating(m):
    if not m.get("ratings"):
        return 0
    return round(sum(m["ratings"]) / len(m["ratings"]), 1)

# ================================
# RANKINGS
# ================================

def get_rankings(data):
    m = data["movies"]

    return {
        "🔥 Trending": sorted(m, key=lambda x: x.get("views",0), reverse=True)[:10],
        "🏆 Top": sorted(m, key=lambda x: avg_rating(x), reverse=True)[:10],
        "🆕 Neu": list(reversed(m))[:10]
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

        requests.post(f"{URL}/sendPhoto", json={
            "chat_id": chat_id,
            "photo": movie.get("Poster") or "https://via.placeholder.com/300x450",
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
            "reply_markup": {
                "inline_keyboard":[[
                    {"text":"▶️ Öffnen","callback_data":f"movie_{movie['Title']}"}
                ]]
            }
        }, timeout=5)

# ================================
# FILM CARD
# ================================

def send_card(chat_id, movie, local):
    title = movie["Title"]
    year = movie["Year"]

    genres = [g.strip() for g in movie.get("Genre","").split(",") if g.strip()]
    if not genres:
        genres = ["Unknown"]

    main = " • ".join(genres[:2])

    plot = generate_story(title, movie.get("Plot"), movie.get("Genre"))

    # SERIES TEXT
    series_text = ""
    if local.get("series"):
        series_text += f"\n📀 {local['series']}"
    if local.get("order"):
        series_text += f" • Teil {local['order']}"
    if local.get("phase"):
        series_text += f" • {local['phase']}"

    caption = f"""🎬 {title.upper()} ({year})
🔥 4K • {main}
━━━━━━━━━━━━━━
⭐ {movie.get("imdbRating")} • ⏱ {movie.get("Runtime")} • 🔞 FSK 16
🎥 {movie.get("Director")}{series_text}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{local["id"]}
━━━━━━━━━━━━━━
#{genres[0]} #{genres[1] if len(genres)>1 else genres[0]} #Neu
@LibraryOfLegends"""

    # BUTTONS
    buttons = []

    if local.get("series"):
        buttons.append([{
            "text": f"🎞 {local['series']} ansehen",
            "callback_data": f"series_{local['series']}"
        }])

    buttons.append([
        {"text":"⭐1","callback_data":f"rate_{local['id']}_1"},
        {"text":"⭐2","callback_data":f"rate_{local['id']}_2"},
        {"text":"⭐3","callback_data":f"rate_{local['id']}_3"}
    ])

    # SEND
    requests.post(f"{URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": movie.get("Poster") or "https://via.placeholder.com/300x450"
    }, timeout=5)

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption,
        "reply_markup": {"inline_keyboard": buttons}
    }, timeout=5)

# ================================
# VIDEO
# ================================

def handle_video(msg):
    data = load_data()

    video = msg.get("video") or msg.get("document")
    title = clean_title(msg.get("caption") or msg.get("document", {}).get("file_name",""))

    movie = get_movie(title)
    if not movie:
        return

    meta = detect_series(movie["Title"])

    entry = {
        "id": str(len(data["movies"])+1).zfill(4),
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
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if not m: return "ok"

            movie = get_movie(title)
            if not movie: return "ok"

            m["views"] += 1
            save_data(data)
            send_card(chat_id, movie, m)

        elif cb.startswith("series_"):
            name = cb.replace("series_","")
            show_grid(chat_id, get_series_list(data, name))

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

# ================================
# START
# ================================

def show_home(chat_id):
    data = load_data()
    rankings = get_rankings(data)

    for name, movies in rankings.items():
        requests.post(f"{URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": name
        }, timeout=5)

        show_grid(chat_id, movies)

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))