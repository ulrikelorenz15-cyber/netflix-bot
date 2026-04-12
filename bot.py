# ================================
# 🎬 NETFLIX BOT FINAL (FIX CLEAN)
# ================================

import os
import json
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

SESSION = {}
USER_STATE = {}

# ================================
# UTILS
# ================================

def safe_post(method, payload):
    try:
        print(f"[SEND] {method}")
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
# SAMPLE DATA (immer vorhanden)
# ================================

def ensure_data():
    data = load_data()

    if not data["movies"]:
        print("👉 Lade Demo Filme...")

        data["movies"] = [
            {
                "id": "0001",
                "title": "Havoc",
                "year": "2025",
                "genre": ["Action", "Thriller"],
                "rating": "7.4",
                "runtime": "125 Min",
                "story": "Ein Ermittler gerät in ein brutales Netz aus Gewalt.",
                "file_id": None,
                "views": 0
            },
            {
                "id": "0002",
                "title": "Fight Club",
                "year": "1999",
                "genre": ["Drama"],
                "rating": "8.8",
                "runtime": "139 Min",
                "story": "Ein Mann gründet einen geheimen Fight Club.",
                "file_id": None,
                "views": 0
            }
        ]

        save_data(data)

# ================================
# SCORE
# ================================

def get_top(data):
    return sorted(data["movies"], key=lambda x: x["views"], reverse=True)

# ================================
# CONTINUE
# ================================

def update_continue(uid, mid):
    USER_STATE.setdefault(uid, [])
    if mid in USER_STATE[uid]:
        USER_STATE[uid].remove(mid)
    USER_STATE[uid].insert(0, mid)

# ================================
# HERO
# ================================

def show_hero(chat_id, m):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"🔥 TOP FILM\n\n🎬 {m['title']}\n⭐ {m['rating']}",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "▶️ Start", "callback_data": f"movie_{m['title']}"}
            ]]
        }
    })

# ================================
# SWIPE
# ================================

def show_swipe(chat_id, movies, index=0):
    print(f"[SWIPE] index={index}")

    if not movies:
        safe_post("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Keine Filme vorhanden"
        })
        return

    SESSION[chat_id] = movies

    index = max(0, min(index, len(movies)-1))
    m = movies[index]

    nav = []
    if index > 0:
        nav.append({"text": "⬅️", "callback_data": f"swipe_{index-1}"})
    if index < len(movies)-1:
        nav.append({"text": "➡️", "callback_data": f"swipe_{index+1}"})

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"🎬 {m['title']}\n⭐ {m['rating']}",
        "reply_markup": {
            "inline_keyboard": [
                nav,
                [{"text": "▶️ Öffnen", "callback_data": f"movie_{m['title']}"}]
            ]
        }
    })

# ================================
# CARD
# ================================

def send_card(chat_id, m):
    print(f"[CARD] {m['title']}")

    caption = f"""🎬 {m['title']} ({m['year']})
🔥 4K • {' • '.join(m['genre'])}
━━━━━━━━━━━━━━
⭐ {m['rating']} • ⏱ {m['runtime']}
━━━━━━━━━━━━━━
📖 STORY
{m['story']}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━"""

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": caption,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "▶️ Play", "callback_data": f"play_{m['id']}"}
            ]]
        }
    })

# ================================
# HOME
# ================================

def show_home(chat_id):
    print("[HOME] geladen")

    data = load_data()
    movies = get_top(data)

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 CLEAN VERSION"
    })

    if movies:
        show_hero(chat_id, movies[0])
        show_swipe(chat_id, movies, 0)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    print("UPDATE:", update)

    data = load_data()

    # CALLBACKS
    if "callback_query" in update:
        cb = update["callback_query"]["data"]
        chat_id = update["callback_query"]["message"]["chat"]["id"]

        print("CALLBACK:", cb)

        if cb.startswith("swipe_"):
            i = int(cb.split("_")[1])
            show_swipe(chat_id, SESSION.get(chat_id, []), i)

        elif cb.startswith("movie_"):
            title = cb.replace("movie_", "")
            m = next((x for x in data["movies"] if x["title"] == title), None)

            if m:
                m["views"] += 1
                save_data(data)
                update_continue(chat_id, m["id"])
                send_card(chat_id, m)

        elif cb.startswith("play_"):
            mid = cb.split("_")[1]
            m = next((x for x in data["movies"] if x["id"] == mid), None)

            if m:
                safe_post("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"▶️ Jetzt läuft: {m['title']}"
                })

    # MESSAGES
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
    print("🔥 CLEAN BOT STARTING...")

    ensure_data()

    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))