# ================================
# 🎬 NETFLIX BOT FINAL (STABLE OFFLINE SYSTEM)
# ================================

import os
import json
import requests
import re
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

TMDB_KEY = os.getenv("TMDB_KEY")  # optional

DATA_FILE = "data.json"
SESSION = {}

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except:
        pass

def clean_text(text):
    return text.replace("\n", " ").strip() if text else ""

# ================================
# 🎬 REAL POSTER
# ================================

def get_poster(title):
    if not TMDB_KEY:
        return f"https://dummyimage.com/600x900/000/fff&text={title.replace(' ','+')}"

    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_KEY, "query": title},
            timeout=5
        ).json()

        if r.get("results"):
            p = r["results"][0].get("poster_path")
            if p:
                return f"https://image.tmdb.org/t/p/w500{p}"
    except:
        pass

    return f"https://dummyimage.com/600x900/000/fff&text={title.replace(' ','+')}"

# ================================
# 🧠 ULTRA PARSER (FIXED)
# ================================

def extract_movie(text):
    text = clean_text(text)

    # TITLE
    title_match = re.search(r"🎬\s*(.*?)\s*\(", text)
    title = title_match.group(1).strip() if title_match else None

    # YEAR
    year_match = re.search(r"\((\d{4})\)", text)
    year = year_match.group(1) if year_match else ""

    # GENRE
    genres = re.findall(r"#(\w+)", text)

    if not genres:
        g = re.search(r"🔥.*?•(.*?)━", text)
        if g:
            genres = [x.strip() for x in g.group(1).split("•")]

    if not genres:
        genres = ["Unknown"]

    # RUNTIME
    runtime_match = re.search(r"⏱\s*([0-9]+ ?min)", text.lower())
    runtime = runtime_match.group(1) if runtime_match else "-"

    # DIRECTOR
    director_match = re.search(r"🎥\s*(.*?)\s*━", text)
    director = director_match.group(1).strip() if director_match else "-"

    # RATING
    rating_match = re.search(r"⭐\s*([0-9.]+)", text)
    rating = rating_match.group(1) if rating_match else "-"

    if not title:
        return None

    return {
        "title": title,
        "year": year,
        "genre": genres[:2],
        "runtime": runtime,
        "director": director,
        "rating": rating
    }

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# 🎬 SAVE MOVIE
# ================================

def save_movie(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie(caption)

    if not info:
        return None

    # DUPLICATE
    for m in data["movies"]:
        if m["title"].lower() == info["title"].lower():
            return m

    entry = {
        "id": get_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)

    return entry

# ================================
# 📊 SCORE
# ================================

def get_top(data):
    return sorted(data["movies"], key=lambda x: x["views"], reverse=True)

# ================================
# 🎮 SWIPE UI
# ================================

def show_swipe(chat_id, movies, i=0):
    SESSION[chat_id] = movies

    if not movies:
        return

    m = movies[i]

    nav = []
    if i > 0:
        nav.append({"text": "⬅️", "callback_data": f"swipe_{i-1}"})
    if i < len(movies)-1:
        nav.append({"text": "➡️", "callback_data": f"swipe_{i+1}"})

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"🎬 {m['title']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎬 CARD (DEIN DESIGN)
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m.get('year','')})
🔥 4K • {' • '.join(m.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {m.get('rating','-')} • ⏱ {m.get('runtime','-')} • 🔞 FSK 16
🎥 {m.get('director','-')}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━
#{' #'.join(m.get('genre',[]))} #Neu
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"])
    })

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m["file_id"],
        "caption": caption
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    top = get_top(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix Style"
    })

    show_swipe(chat_id, top[:10])

# ================================
# VIDEO
# ================================

def handle_video(msg):
    m = save_movie(msg)

    if not m:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Fehler beim Erkennen"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"✅ Gespeichert: {m['title']}"
    })

    send_card(msg["chat"]["id"], m)
    send_card(CHANNEL, m)

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

        if cb.startswith("swipe_"):
            i = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), i)

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