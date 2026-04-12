# ================================
# 🎬 NETFLIX BOT FINAL (ULTRA FIXED MATCH SYSTEM FINAL)
# ================================

import os
import json
import requests
import re
from flask import Flask, request
from openai import OpenAI
from difflib import get_close_matches

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
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

def clean_text(text):
    if not text:
        return ""

    text = text.lower()

    blacklist = [
        "1080p","720p","bluray","x264","x265",
        "dvdrip","webdl","german","dl","hdrip",
        "hevc","4k"
    ]

    text = text.replace(".", " ").replace("-", " ")

    words = text.split()
    return " ".join([w for w in words if w not in blacklist])

# ================================
# 🧠 ULTRA TITLE EXTRACTOR
# ================================

def extract_title_ultra(msg):
    caption = msg.get("caption") or ""
    filename = msg.get("document", {}).get("file_name", "")

    # 🎬 PRIORITY: 🎬 TITLE
    m = re.search(r"🎬\s*([^\(\n]+)", caption)
    if m:
        return m.group(1).strip()

    # 🧠 FALLBACK: FIRST LINE
    first_line = caption.split("\n")[0]
    first_line = re.sub(r"[^\w\s]", "", first_line)
    if len(first_line.split()) <= 5:
        return first_line.strip()

    # 📂 FILE NAME
    if filename:
        return clean_text(filename)

    return clean_text(caption)

# ================================
# 🧠 AI GENRE
# ================================

def ai_detect_genre(title):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Genres für Film: {title}. Nur 2 Genres."
            }]
        )
        return [g.strip() for g in res.choices[0].message.content.split(",")]
    except:
        return ["Unknown"]

# ================================
# 🎬 POSTER
# ================================

def generate_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# 🧠 SAVE MOVIE (FIXED)
# ================================

def save_movie_from_post(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    title = extract_title_ultra(msg)

    if not title or len(title) < 2:
        return None

    # YEAR
    caption = msg.get("caption") or ""
    year = ""
    y = re.search(r"\((\d{4})\)", caption)
    if y:
        year = y.group(1)

    # GENRE
    genres = re.findall(r"#(\w+)", caption)
    if not genres:
        genres = ai_detect_genre(title)

    # DUPLICATE CHECK
    for m in data["movies"]:
        if m["title"].lower() == title.lower():
            return m

    entry = {
        "id": get_next_id(data),
        "title": title,
        "year": year,
        "genre": genres[:2],
        "runtime": "-",
        "director": "-",
        "rating": "-",
        "file_id": video["file_id"],
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)

    return entry

# ================================
# 📊 SCORE
# ================================

def get_score(m):
    return m.get("views", 0) * 1.5 + len(m.get("genre", [])) * 2

def get_top_movies(data):
    return sorted(data["movies"], key=get_score, reverse=True)[:10]

# ================================
# 🎮 SWIPE UI
# ================================

def show_swipe(chat_id, movies, index=0):
    SESSION[chat_id] = movies

    if not movies:
        return

    m = movies[index]

    nav = []
    if index > 0:
        nav.append({"text": "⬅️", "callback_data": f"swipe_{index-1}"})
    if index < len(movies)-1:
        nav.append({"text": "➡️", "callback_data": f"swipe_{index+1}"})

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": generate_poster(m["title"]),
        "caption": f"🎬 {m['title']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎬 CARD
# ================================

def send_card(chat_id, movie):
    caption = f"""🎬 {movie['title'].upper()} ({movie.get('year','')})
🔥 4K • {' • '.join(movie.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {movie.get('rating','-')} • ⏱ {movie.get('runtime','-')}
━━━━━━━━━━━━━━
▶️ #{movie['id']}
━━━━━━━━━━━━━━
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": generate_poster(movie["title"])
    })

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": movie["file_id"],
        "caption": caption
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 FINAL SYSTEM"
    })

    show_swipe(chat_id, get_top_movies(data))

# ================================
# VIDEO
# ================================

def handle_video(msg):
    entry = save_movie_from_post(msg)

    if not entry:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Film konnte nicht erkannt werden"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"🔥 ERKANNT: {entry['title']}"
    })

    send_card(msg["chat"]["id"], entry)
    send_card(CHANNEL, entry)

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

        if cb == "home":
            show_home(chat_id)

        elif cb.startswith("swipe_"):
            index = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), index)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if m:
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            show_home(msg["chat"]["id"])

        if "video" in msg or "document" in msg:
            handle_video(msg)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))