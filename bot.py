# ================================
# 🎬 NETFLIX BOT FINAL (ULTIMATE CLEAN SYSTEM)
# ================================

import os
import json
import requests
import re
from flask import Flask, request
from openai import OpenAI

# ================================
# CONFIG
# ================================

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"

TMDB_KEY = os.getenv("TMDB_KEY")  # optional
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
# 🎬 POSTER
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
# 🧠 AI GENERATOR
# ================================

def ai_generate(title):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Film: {title}\nGenre, Laufzeit, Regisseur, Rating, Story"
            }]
        )

        text = res.choices[0].message.content

        return {
            "genre": ["Action","Drama"],
            "runtime": "120 Min",
            "director": "-",
            "rating": "7.0",
            "story": text
        }

    except:
        return {
            "genre": ["Action"],
            "runtime": "120 Min",
            "director": "-",
            "rating": "7.0",
            "story": "-"
        }

# ================================
# 🧠 PARSER (DEIN FORMAT)
# ================================

def extract_movie(text):
    if not text:
        return None

    title = re.search(r"🎬\s*(.*?)\s*\(", text)
    year = re.search(r"\((\d{4})\)", text)
    rating = re.search(r"⭐\s*([0-9.]+)", text)
    runtime = re.search(r"⏱\s*([0-9]+\s*Min)", text)
    director = re.search(r"🎥\s*(.*?)\n", text)
    story = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━━━━━━━", text, re.S)
    genre = re.findall(r"#(\w+)", text)

    if not title:
        return None

    return {
        "title": title.group(1).strip(),
        "year": year.group(1) if year else "",
        "genre": genre[:2] if genre else ["Unknown"],
        "runtime": runtime.group(1) if runtime else "-",
        "director": director.group(1) if director else "-",
        "rating": rating.group(1) if rating else "-",
        "story": story.group(1).strip() if story else "-",
        "tags": genre
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
# SAVE
# ================================

def save_movie(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption") or ""

    info = extract_movie(caption)

    if not info:
        return None

    for m in data["movies"]:
        if m["title"].lower() == info["title"].lower():
            return m

    entry = {
        "id": get_id(data),
        **info,
        "file_id": video["file_id"] if video else None,
        "views": 0,
        "series": detect_series(info["title"])
    }

    data["movies"].append(entry)
    save_data(data)

    return entry

# ================================
# SERIES
# ================================

def detect_series(title):
    t = title.lower()
    if "bourne" in t:
        return "Bourne"
    if "jurassic" in t:
        return "Jurassic"
    return None

# ================================
# CONTINUE
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
# UI
# ================================

def show_row(chat_id, title, movies):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    buttons = [[
        {"text": m["title"][:15], "callback_data": f"movie_{m['title']}"}
        for m in movies[:5]
    ]]

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": " ",
        "reply_markup": {"inline_keyboard": buttons}
    })

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
# CARD (FINAL DESIGN)
# ================================

def send_card(chat_id, m):
    caption = f"""🎬 {m['title'].upper()} ({m.get('year','')})
🔥 4K • {' • '.join(m.get('genre',[]))}
━━━━━━━━━━━━━━
⭐ {m.get('rating','-')} • ⏱ {m.get('runtime','-')} • 🔞 FSK 16
🎥 {m.get('director','-')}
━━━━━━━━━━━━━━
📖 STORY
{m.get('story','-')}
━━━━━━━━━━━━━━
▶️ #{m['id']}
━━━━━━━━━━━━━━
{' '.join([f'#{t}' for t in m.get('tags',[])])} #Neu
@LibraryOfLegends"""

    safe_post("sendPhoto", {
        "chat_id": chat_id,
        "photo": get_poster(m["title"])
    })

    if m.get("file_id"):
        safe_post("sendVideo", {
            "chat_id": chat_id,
            "video": m["file_id"],
            "caption": caption
        })
    else:
        safe_post("sendMessage", {
            "chat_id": chat_id,
            "text": caption
        })

# ================================
# HOME
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix Style"
    })

    cont = get_continue(chat_id, data)
    if cont:
        show_row(chat_id, "▶️ Weiter schauen", cont)

    top = sorted(data["movies"], key=lambda x: x["views"], reverse=True)

    show_swipe(chat_id, top[:10])
    show_row(chat_id, "🆕 Neu", list(reversed(data["movies"]))[:10])

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
                update_continue(chat_id, m["id"])
                m["views"] += 1
                save_data(data)
                send_card(chat_id, m)

    if "message" in update:
        msg = update["message"]

        if msg.get("text") == "/start":
            show_home(msg["chat"]["id"])

        if msg.get("text", "").startswith("/add"):
            title = msg["text"].replace("/add","").strip()
            ai = ai_generate(title)

            data = load_data()

            entry = {
                "id": get_id(data),
                "title": title,
                "year": "",
                "genre": ai["genre"],
                "runtime": ai["runtime"],
                "director": ai["director"],
                "rating": ai["rating"],
                "story": ai["story"],
                "tags": ai["genre"],
                "file_id": None,
                "views": 0
            }

            data["movies"].append(entry)
            save_data(data)

            send_card(msg["chat"]["id"], entry)

        if "video" in msg or "document" in msg:
            m = save_movie(msg)

            if m:
                send_card(msg["chat"]["id"], m)
                send_card(CHANNEL, m)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))