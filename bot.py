# ================================
# 🎬 NETFLIX BOT FINAL (UI MAX MODE)
# ================================

import os
import json
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

DATA_FILE = "data.json"

SESSION = {}
USER_STATE = {}

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
            path = r["results"][0].get("poster_path")
            if path:
                return f"https://image.tmdb.org/t/p/w500{path}"
    except:
        pass

    return f"https://dummyimage.com/600x900/000/fff&text={title}"

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
# 📊 SCORE
# ================================

def get_score(m):
    return m["views"] * 2

def get_top(data):
    return sorted(data["movies"], key=get_score, reverse=True)

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
# 🎬 HERO BANNER
# ================================

def show_hero(chat_id, m):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🔥 TOP PICK

🎬 {m['title']}
⭐ {m['rating']}

{m.get('story','Jetzt verfügbar')}""",
        "reply_markup": {
            "inline_keyboard":[[
                {"text":"▶️ Start","callback_data":f"movie_{m['title']}"}
            ]]
        }
    })

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
        nav.append({"text":"⬅️","callback_data":f"swipe_{index-1}"})
    if index < len(movies)-1:
        nav.append({"text":"➡️","callback_data":f"swipe_{index+1}"})

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🎬 {m['title']}
⭐ {m['rating']}""",
        "reply_markup":{
            "inline_keyboard":[
                nav,
                [{"text":"▶️ Öffnen","callback_data":f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# 🎥 PREVIEW (FAKE HOVER)
# ================================

def show_preview(chat_id, m):
    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"]),
        "caption": f"""🎬 {m['title']}

{m.get('story','')}""",
        "reply_markup":{
            "inline_keyboard":[[
                {"text":"▶️ Start","callback_data":f"movie_{m['title']}"}
            ]]
        }
    })

# ================================
# 🎬 FULL CARD
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title']} ({m['year']})
🔥 4K • {' • '.join(m['genre'])}
━━━━━━━━━━━━━━
⭐ {m['rating']} • ⏱ {m['runtime']}
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

    safe_post("sendVideo", {
        "chat_id": chat_id,
        "video": m.get("file_id"),
        "caption": caption
    })

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
# 🏠 HOME
# ================================

def show_home(chat_id):
    data = load_data()
    top = get_top(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix UI MAX"
    })

    if top:
        show_hero(chat_id, top[0])

    cont = get_continue(chat_id, data)
    if cont:
        show_swipe(chat_id, cont, 0)

    show_swipe(chat_id, top, 0)

    for name, movies in get_categories(data).items():
        show_swipe(chat_id, movies[:10], 0)

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except:
        pass

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
            title = cb.replace("movie_","")
            m = next((x for x in data["movies"] if x["title"] == title),None)

            if m:
                update_continue(chat_id, m["id"])
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            show_home(msg["chat"]["id"])

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 NETFLIX UI MAX RUNNING")
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))