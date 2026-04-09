# ================================
# 🎬 NETFLIX BOT FINAL (ULTRA GOD MODE V2)
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
    return " ".join([w for w in raw.split() if w.lower() not in blacklist])

# ================================
# 🧠 LOCAL DATABASE (FAST MATCH)
# ================================

LOCAL_DB = {
    "bourne": "The Bourne Identity",
    "bourne identity": "The Bourne Identity",
    "bourne supremacy": "The Bourne Supremacy",
    "bourne ultimatum": "The Bourne Ultimatum",
    "jurassic": "Jurassic Park",
    "jp": "Jurassic Park",
    "godfather": "The Godfather",
    "shawshank": "The Shawshank Redemption"
}

def local_match(title):
    t = title.lower()
    for key in LOCAL_DB:
        if key in t:
            return LOCAL_DB[key]
    return None

# ================================
# 🧠 AI DETECT
# ================================

def ai_detect_title(raw_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Errate den Film Titel:\n{raw_text}\nNur Titel."
            }],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except:
        return None

def ai_match_movie(raw_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Welcher Film ist gemeint:\n{raw_text}\nNur Titel."
            }],
            temperature=0.4
        )
        return res.choices[0].message.content.strip()
    except:
        return None

# ================================
# 🎯 POSTER DETECT
# ================================

def detect_from_image(file_id):
    try:
        file_info = requests.get(f"{URL}/getFile?file_id={file_id}").json()
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Welcher Film ist dieses Poster?\n{file_url}\nNur Titel."
            }]
        )

        return res.choices[0].message.content.strip()

    except:
        return None

# ================================
# MATCH ENGINE
# ================================

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
# SERIES
# ================================

SERIES_DB = {
    "Bourne": ["bourne"],
    "Jurassic Park": ["jurassic"]
}

def detect_series(title):
    t = title.lower()
    for name, keys in SERIES_DB.items():
        if any(k in t for k in keys):
            return {"series": name, "order": 0, "phase": None}
    return {"series": None, "order": 0, "phase": None}

def get_series_list(data, name):
    return [m for m in data["movies"] if m.get("series") == name]

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

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# OMDb
# ================================

def get_movie(title):
    if title in CACHE:
        return CACHE[title]

    try:
        r = requests.get(
            f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}",
            timeout=5
        ).json()

        if r.get("Response") == "False":
            return None

        CACHE[title] = r
        return r

    except:
        return None

# ================================
# STORY
# ================================

def generate_story(title, plot, genre):
    return f"{title} entwickelt sich zu einer intensiven Geschichte voller Konflikte und Konsequenzen."

# ================================
# UI
# ================================

def show_grid(chat_id, movies):
    for m in movies[:3]:
        movie = get_movie(m["title"])
        if not movie:
            continue

        safe_post("sendPhoto", {
            "chat_id": chat_id,
            "photo": movie.get("Poster"),
            "caption": f"{movie['Title']} ⭐ {movie['imdbRating']}"
        })

# ================================
# CARD
# ================================

def send_card(chat_id, movie, local):
    caption = f"{movie['Title']} ({movie['Year']})\n⭐ {movie['imdbRating']}"
    
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
# VIDEO (ULTRA ENGINE)
# ================================

def handle_video(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    raw = extract_title_advanced(msg)
    movie = None

    # 1 LOCAL
    if raw:
        local = local_match(raw)
        if local:
            movie = try_multiple_titles(local)

    # 2 NORMAL
    if not movie and raw:
        movie = try_multiple_titles(raw)

    # 3 AI GUESS
    if not movie and raw:
        ai_title = ai_detect_title(raw)
        if ai_title:
            movie = try_multiple_titles(ai_title)

    # 4 FULL AI
    if not movie and raw:
        ai_full = ai_match_movie(raw)
        if ai_full:
            movie = try_multiple_titles(ai_full)

    # 5 POSTER
    if not movie:
        vision = detect_from_image(video["file_id"])
        if vision:
            movie = try_multiple_titles(vision)

    if not movie:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": f"❌ Film nicht erkannt\n{raw}"
        })
        return

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0
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

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            safe_post("sendMessage", {
                "chat_id": msg["chat"]["id"],
                "text": "🎬 Bot läuft"
            })

        if "video" in msg or "document" in msg:
            handle_video(msg)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))