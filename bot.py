# ================================
# 🎬 NETFLIX BOT FINAL (ULTRA UI)
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

DATA_FILE = "data.json"

SESSION = {}
USER_STATE = {}

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except Exception as e:
        print("ERROR:", e)

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
# 🎬 POSTER (REAL)
# ================================

def get_poster(title):
    if not TMDB_KEY:
        return f"https://dummyimage.com/600x900/000/fff&text={title}"

    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_KEY, "query": title},
            timeout=5
        ).json()

        if r.get("results"):
            path = r["results"][0].get("poster_path")
            if path:
                return f"https://image.tmdb.org/t/p/w500{path}"
    except:
        pass

    return f"https://dummyimage.com/600x900/000/fff&text={title}"

# ================================
# 🧠 PARSER
# ================================

def extract_movie_data(text):
    if not text:
        return None

    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t:
        return None

    title = t.group(1).strip()
    year = t.group(2)

    rating = re.search(r"⭐\s*([0-9.]+)", text)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    director = re.search(r"🎥\s*(.*?)\n", text)

    story_match = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)
    story = story_match.group(1).strip() if story_match else "-"

    genres = re.findall(r"#(\w+)", text)
    if not genres:
        g = re.search(r"🔥.*?•(.*?)\n", text)
        if g:
            genres = [x.strip() for x in g.group(1).split("•")]

    return {
        "title": title,
        "year": year,
        "genre": genres[:2] if genres else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1).strip() if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story
    }

# ================================
# SAVE
# ================================

def save_movie(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie_data(caption)
    if not info:
        return None

    for m in data["movies"]:
        if m["title"].lower() == info["title"].lower():
            return m

    entry = {
        "id": get_id(data),
        **info,
        "file_id": video["file_id"],
        "views": 0,
        "timestamp": time.time()
    }

    data["movies"].append(entry)
    save_data(data)

    return entry

# ================================
# 📊 TRENDING
# ================================

def get_score(m):
    return m["views"] * 2 + (5 - (time.time() - m["timestamp"]) / 86400)

def get_trending(data):
    return sorted(data["movies"], key=get_score, reverse=True)

# ================================
# 📂 CATEGORIES
# ================================

def get_categories(data):
    cats = {}
    for m in data["movies"]:
        for g in m["genre"]:
            cats.setdefault(g, []).append(m)
    return cats

# ================================
# ▶️ CONTINUE
# ================================

def update_continue(uid, mid):
    USER_STATE.setdefault(uid, [])
    if mid in USER_STATE[uid]:
        USER_STATE[uid].remove(mid)
    USER_STATE[uid].insert(0, mid)

def get_continue(uid, data):
    ids = USER_STATE.get(uid, [])
    return [m for m in data["movies"] if m["id"] in ids]

# ================================
# 🎮 GRID ROW (NETFLIX STYLE)
# ================================

def show_grid(chat_id, title, movies):
    if not movies:
        return

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    for m in movies[:6]:
        safe_post("sendPhoto", {
            "chat_id": chat_id,
            "photo": get_poster(m["title"]),
            "caption": f"🎬 {m['title']}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "▶️", "callback_data": f"preview_{m['title']}"}
                ]]
            }
        })

# ================================
# PREVIEW
# ================================

def show_preview(chat_id, m):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🎬 {m['title']}
⭐ {m['rating']}

{m['story']}""",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}
            ]]
        }
    })

# ================================
# CARD
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title']} ({m['year']})
🔥 4K • {' • '.join(m['genre'])}
━━━━━━━━━━━━━━
⭐ {m['rating']} • ⏱ {m['runtime']}
━━━━━━━━━━━━━━
📖 STORY
{m['story']}
━━━━━━━━━━━━━━
▶️ #{m['id']}"""

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m["file_id"],
        "caption": caption
    })

# ================================
# 🏠 HOME
# ================================

def show_home(chat_id):
    data = load_data()
    trending = get_trending(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Netflix UI ULTRA"
    })

    # HERO
    if trending:
        show_preview(chat_id, trending[0])

    # CONTINUE
    cont = get_continue(chat_id, data)
    if cont:
        show_grid(chat_id, "▶️ Continue Watching", cont)

    # TRENDING
    show_grid(chat_id, "🔥 Trending", trending)

    # GENRES
    for name, movies in get_categories(data).items():
        show_grid(chat_id, f"🎬 {name}", movies)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    data = load_data()

    if "callback_query" in update:
        cb = update["callback_query"]["data"]
        chat_id = update["callback_query"]["message"]["chat"]["id"]

        if cb.startswith("preview_"):
            title = cb.replace("preview_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)
            if m:
                show_preview(chat_id, m)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                m["views"] += 1
                update_continue(chat_id, m["id"])
                save_data(data)
                send_card(chat_id, m)

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if msg.get("text") == "/start":
            show_home(chat_id)

        if "video" in msg or "document" in msg:
            entry = save_movie(msg)

            if not entry:
                safe_post("sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Fehler beim Erkennen"
                })
                return "ok"

            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ Gespeichert: {entry['title']}"
            })

            send_card(chat_id, entry)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 ULTRA UI RUNNING")

    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))