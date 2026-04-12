# ================================
# 🎬 NETFLIX BOT FINAL (DESIGN PACK + APP MODE)
# ================================

import os
import json
import requests
import re
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
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
    except:
        pass

# ================================
# 🎬 POSTER (ECHT)
# ================================

def get_poster(title):
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

    return f"https://dummyimage.com/600x900/000/fff&text={title}"

# ================================
# 🧠 PARSER (PERFECT MATCH)
# ================================

def extract_movie_data(text):
    if not text:
        return None

    raw = text

    title = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", raw)
    if not title:
        return None

    name = title.group(1).strip()
    year = title.group(2)

    rating = re.search(r"⭐\s*([0-9.]+)", raw)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", raw)
    director = re.search(r"🎥\s*(.*?)\s*━━━━━━━━", raw)
    story = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", raw, re.S)

    genres = re.findall(r"#(\w+)", raw)

    return {
        "title": name,
        "year": year,
        "genre": genres[:2] if genres else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1) if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story.group(1).strip() if story else "-",
        "tags": genres if genres else ["Unknown"]
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
# SAVE MOVIE
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
        "views": 0
    }

    data["movies"].append(entry)
    save_data(data)
    return entry

# ================================
# 📊 SORTING
# ================================

def get_top(data):
    return sorted(data["movies"], key=lambda x: x["views"], reverse=True)

# ================================
# 📂 KATEGORIEN
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
    USER_STATE[uid] = USER_STATE[uid][:5]

def get_continue(uid, data):
    ids = USER_STATE.get(uid, [])
    return [m for m in data["movies"] if m["id"] in ids]

# ================================
# 🎮 GRID
# ================================

def show_grid(chat_id, movies, page=0, title="🎬 Auswahl"):
    SESSION[chat_id] = movies

    per_page = 9
    start = page * per_page
    subset = movies[start:start+per_page]

    rows = []
    row = []

    for m in subset:
        row.append({
            "text": "🎬",
            "callback_data": f"preview_{m['title']}"
        })
        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"page_{page-1}"})
    if start + per_page < len(movies):
        nav.append({"text": "➡️", "callback_data": f"page_{page+1}"})

    if nav:
        rows.append(nav)

    rows.append([{"text": "🏠 Home", "callback_data": "home"}])

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": title,
        "reply_markup": {"inline_keyboard": rows}
    })

# ================================
# 🎥 PREVIEW
# ================================

def show_preview(chat_id, title):
    data = load_data()
    m = next((x for x in data["movies"] if x["title"] == title), None)

    if not m:
        return

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"🎬 {m['title']}\n⭐ {m['rating']}",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}],
                [{"text": "🔙 Zurück", "callback_data": "home"}]
            ]
        }
    })

# ================================
# 🎬 FILMKARTE (PERFEKT)
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m['year']})
🔥 4K • {' • '.join(m['genre'])}
━━━━━━━━━━━━━━
⭐ {m['rating']} • ⏱ {m['runtime']} • 🔞 FSK 16
🎥 {m['director']}
━━━━━━━━━━━━━━
📖 STORY
{m['story']}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━
{' '.join(['#'+g for g in m['tags']])}
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
# 🏠 HOME
# ================================

def show_home(chat_id):
    keyboard = [
        [{"text": "🔥 Trending", "callback_data": "trending"}],
        [{"text": "🎬 Kategorien", "callback_data": "categories"}],
        [{"text": "▶️ Continue", "callback_data": "continue"}]
    ]

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 NETFLIX UI",
        "reply_markup": {"inline_keyboard": keyboard}
    })

# ================================
# VIDEO
# ================================

def handle_video(msg):
    entry = save_movie(msg)

    if not entry:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": "❌ Format falsch"
        })
        return

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"✅ Gespeichert: {entry['title']}"
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

        elif cb == "trending":
            show_grid(chat_id, get_top(data), 0, "🔥 Trending")

        elif cb == "categories":
            cats = get_categories(data)
            buttons = [[{"text": c, "callback_data": f"cat_{c}"}] for c in cats]

            safe_post("sendMessage", {
                "chat_id": chat_id,
                "text": "🎬 Kategorien",
                "reply_markup": {"inline_keyboard": buttons}
            })

        elif cb.startswith("cat_"):
            name = cb.replace("cat_", "")
            show_grid(chat_id, get_categories(data)[name], 0, f"🎬 {name}")

        elif cb == "continue":
            show_grid(chat_id, get_continue(chat_id, data), 0, "▶️ Continue")

        elif cb.startswith("page_"):
            show_grid(chat_id, SESSION.get(chat_id, []), int(cb.split("_")[1]))

        elif cb.startswith("preview_"):
            show_preview(chat_id, cb.replace("preview_", ""))

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                update_continue(chat_id, m["id"])
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