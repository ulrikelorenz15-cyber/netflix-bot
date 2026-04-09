# ================================
# 🎬 NETFLIX BOT FINAL (MASTER ALL-IN GOD MODE)
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
CACHE = {}
SESSION = {}

# ================================
# UTILS
# ================================

def log_error(e):
    print("ERROR:", str(e))

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except Exception as e:
        log_error(e)

def clean_title(raw):
    if not raw:
        return ""

    raw = raw.replace(".", " ")

    blacklist = ["1080p","720p","bluray","x264","x265","dvdrip","webdl"]
    words = raw.split()

    cleaned = [w for w in words if w.lower() not in blacklist]

    return " ".join(cleaned)

# ================================
# 🧠 AI DETECT GOD MODE
# ================================

def ai_detect_title(raw_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"""
Errate den Film Titel:

{raw_text}

Nur Titel zurückgeben.
"""
            }],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        log_error(e)
        return None

def try_multiple_titles(title):
    variants = [
        title,
        title.split("(")[0],
        title.split("-")[0],
        " ".join(title.split(" ")[:2])
    ]

    for t in variants:
        movie = get_movie(t.strip())
        if movie:
            return movie

    return None

def extract_title_advanced(msg):
    if msg.get("caption"):
        return clean_title(msg.get("caption"))

    if msg.get("document") and msg["document"].get("file_name"):
        return clean_title(msg["document"]["file_name"])

    if "forward_origin" in msg:
        return str(msg["forward_origin"])

    return ""

# ================================
# 🎞 SERIES
# ================================

SERIES_DB = {
    "Bourne": ["bourne"],
    "Jurassic Park": ["jurassic"]
}

MARVEL = ["avengers","iron man","thor","captain america","guardians"]

def detect_series(title):
    t = title.lower()

    for name, keys in SERIES_DB.items():
        if any(k in t for k in keys):
            return {"series": name, "order": 0, "phase": None}

    if any(m in t for m in MARVEL):
        return {"series": "Marvel", "order": 0, "phase": "MCU"}

    return {"series": None, "order": 0, "phase": None}

def get_series_list(data, name):
    return [m for m in data["movies"] if m.get("series") == name]

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

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

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
            messages=[{
                "role":"user",
                "content":f"""
Film: {title}
Genre: {genre}
Inhalt:
{plot}

4-5 Sätze, konkret, düster, Netflix Stil
"""
            }],
            temperature=1.1
        )

        text = res.choices[0].message.content.strip()

        if len(text) < 100:
            raise Exception()

        return text

    except:
        return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte und Konsequenzen."

# ================================
# RATING
# ================================

def avg_rating(m):
    if not m.get("ratings"):
        return 0
    return round(sum(m["ratings"]) / len(m["ratings"]), 1)

# ================================
# GRID
# ================================

def show_grid(chat_id, movies):
    SESSION[chat_id] = movies

    for m in movies[:3]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        safe_post("sendPhoto", {
            "chat_id": chat_id,
            "photo": movie.get("Poster"),
            "caption": f"🎬 {movie['Title']} • ⭐ {movie['imdbRating']}",
            "reply_markup":{
                "inline_keyboard":[[
                    {"text":"▶️ Öffnen","callback_data":f"movie_{movie['Title']}"}
                ]]
            }
        })

# ================================
# 🎬 FILM CARD
# ================================

def send_card(chat_id, movie, local):
    title = movie.get("Title")
    year = movie.get("Year")

    genres = [g.strip() for g in movie.get("Genre","").split(",") if g.strip()]
    if not genres:
        genres = ["Unknown"]

    plot = generate_story(title, movie.get("Plot"), movie.get("Genre"))

    series_text = ""
    if local.get("series"):
        series_text += f"\n📀 {local['series']}"
    if local.get("phase"):
        series_text += f" • {local['phase']}"

    caption = f"""🎬 {title.upper()} ({year})
🔥 4K • {' • '.join(genres[:2])}
━━━━━━━━━━━━━━
⭐ {movie.get("imdbRating")} • 👤 {avg_rating(local)} • ⏱ {movie.get("Runtime")}
🎥 {movie.get("Director")}{series_text}
━━━━━━━━━━━━━━
📖 STORY
{plot}
━━━━━━━━━━━━━━
▶️ #{local.get("id")}
━━━━━━━━━━━━━━
#{genres[0]} #{genres[1] if len(genres)>1 else genres[0]} #Neu
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": movie.get("Poster")
    })

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": local["file_id"],
        "caption": caption
    })

# ================================
# VIDEO (GOD MODE)
# ================================

def handle_video(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    raw = extract_title_advanced(msg)
    movie = None

    if raw:
        movie = try_multiple_titles(raw)

    if not movie and raw:
        ai_title = ai_detect_title(raw)
        if ai_title:
            movie = try_multiple_titles(ai_title)

    if not movie:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": f"❌ Film nicht erkannt\n\nInput: {raw or 'leer'}"
        })
        return

    meta = detect_series(movie["Title"])

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

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"🧠 Erkannt: {movie['Title']}"
    })

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

            if m:
                movie = get_movie(title)
                m["views"] += 1
                save_data(data)
                send_card(chat_id, movie, m)

        elif cb.startswith("series_"):
            name = cb.replace("series_","")
            show_grid(chat_id, get_series_list(data, name))

    msg = update.get("message")

    if msg and msg.get("text") == "/start":
        show_home(msg["chat"]["id"])

    if msg and ("video" in msg or "document" in msg):
        handle_video(msg)

    return "ok"

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix Style UI"
    })

    show_grid(chat_id, data["movies"])

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))