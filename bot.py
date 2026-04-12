# ================================
# 🎬 NETFLIX BOT FINAL (PRO UI)
# ================================

import os
import json
import requests
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

# ================================
# POSTER (REAL)
# ================================

def get_poster(title):
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
# TRENDING SYSTEM
# ================================

def get_score(m):
    # Views + Zeitbonus (neuere Filme pushen)
    age_bonus = 1
    if m.get("timestamp"):
        age = time.time() - m["timestamp"]
        age_bonus = max(1, 5 - (age / 86400))  # Tage

    return m.get("views", 0) * 2 + age_bonus

def get_trending(data):
    return sorted(data["movies"], key=get_score, reverse=True)

# ================================
# KATEGORIEN
# ================================

def get_categories(data):
    cats = {}
    for m in data["movies"]:
        for g in m.get("genre", []):
            cats.setdefault(g, []).append(m)
    return cats

# ================================
# CONTINUE WATCHING
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
# HERO BANNER
# ================================

def show_hero(chat_id, m):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🔥 TRENDING NOW

🎬 {m['title']}
⭐ {m.get('rating','-')}

{m.get('story','Jetzt verfügbar')}""",
        "reply_markup": {
            "inline_keyboard":[[
                {"text":"▶️ Start","callback_data":f"movie_{m['title']}"}
            ]]
        }
    })

# ================================
# ROW SYSTEM (COVER STYLE)
# ================================

def show_row(chat_id, title, movies):
    if not movies:
        return

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    buttons = []
    row = []

    for m in movies[:6]:
        row.append({
            "text": "🎬",
            "callback_data": f"preview_{m['title']}"
        })

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": " ",
        "reply_markup": {"inline_keyboard": buttons}
    })

# ================================
# PREVIEW (HOVER FAKE)
# ================================

def show_preview(chat_id, m):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🎬 {m['title']}
⭐ {m.get('rating','-')}

{m.get('story','')}""",
        "reply_markup":{
            "inline_keyboard":[[
                {"text":"▶️ Öffnen","callback_data":f"movie_{m['title']}"}
            ]]
        }
    })

# ================================
# FULL CARD
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title']} ({m.get('year','')})
🔥 4K • {' • '.join(m.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {m.get('rating','-')} • ⏱ {m.get('runtime','-')}
━━━━━━━━━━━━━━
📖 STORY
{m.get('story','')}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"])
    })

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": caption
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()
    trending = get_trending(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 PRO UI"
    })

    if trending:
        show_hero(chat_id, trending[0])

    # Continue Watching
    cont = get_continue(chat_id, data)
    if cont:
        show_row(chat_id, "▶️ Continue Watching", cont)

    # Trending
    show_row(chat_id, "🔥 Trending", trending)

    # Kategorien
    for name, movies in get_categories(data).items():
        show_row(chat_id, f"🎬 {name}", movies)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    data = load_data()

    print("UPDATE:", update)

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

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 PRO UI BOT RUNNING")
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))