# ================================
# 🎬 NETFLIX FINAL UI SYSTEM
# ================================

import os
import json
import requests
import re
import time
import threading
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None
DATA_FILE = "data.json"

LOGS = []
USER_STATE = {}

# ================================
# LOGGER
# ================================

def log(msg):
    print(msg)
    LOGS.append(str(msg))
    if len(LOGS) > 200:
        LOGS.pop(0)

# ================================
# DATA
# ================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            return json.load(open(DATA_FILE))
    except Exception as e:
        log(f"LOAD ERROR: {e}")
    return {"movies": []}

def save_data(data):
    try:
        json.dump(data, open(DATA_FILE, "w"))
    except Exception as e:
        log(f"SAVE ERROR: {e}")

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# SAFE REGEX
# ================================

def safe(pattern, text):
    try:
        m = re.search(pattern, text, re.S)
        return m.group(1).strip() if m else "-"
    except:
        return "-"

# ================================
# PARSER (FIXED)
# ================================

def extract(text):
    try:
        t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
        if not t:
            return None

        genres = re.findall(r"#(\w+)", text)

        if not genres:
            g = re.search(r"🔥.*?•(.*?)━", text)
            if g:
                genres = [x.strip() for x in g.group(1).split("•")]

        if not genres:
            genres = ["Action", "Unknown"]

        return {
            "title": t.group(1).strip(),
            "year": t.group(2),
            "rating": safe(r"⭐\s*([0-9.]+)", text),
            "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
            "genre": genres[:2],
            "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
        }

    except Exception as e:
        log(f"PARSER ERROR: {e}")
        return None

# ================================
# POSTER
# ================================

def get_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

# ================================
# SCORING (TRENDING)
# ================================

def score(m):
    return m["views"] * 2 + (5 - (time.time() - m["timestamp"]) / 86400)

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
# WEB UI (NETFLIX STYLE)
# ================================

@app.route("/")
def home():
    data = load_data()["movies"]

    trending = sorted(data, key=score, reverse=True)[:10]

    categories = {}
    for m in data:
        for g in m["genre"]:
            categories.setdefault(g, []).append(m)

    return render_template_string("""
    <html>
    <head>
    <style>
    body {background:#141414;color:white;font-family:sans-serif}
    h2 {margin-left:20px}
    .row {display:flex;overflow-x:auto;padding:20px}
    .card {margin-right:10px;transition:0.3s}
    .card img {width:150px;border-radius:8px}
    .card:hover {transform:scale(1.2)}
    </style>
    </head>
    <body>

    <h1 style="margin-left:20px;">🎬 Netflix UI</h1>

    <h2>🔥 Trending</h2>
    <div class="row">
    {% for m in trending %}
        <div class="card">
            <img src="{{m.poster}}">
        </div>
    {% endfor %}
    </div>

    {% for name, movies in categories.items() %}
        <h2>🎬 {{name}}</h2>
        <div class="row">
        {% for m in movies[:10] %}
            <div class="card">
                <img src="{{m.poster}}">
            </div>
        {% endfor %}
        </div>
    {% endfor %}

    </body>
    </html>
    """, trending=trending, categories=categories)

# ================================
# API
# ================================

@app.route("/api/movies")
def api_movies():
    return jsonify(load_data()["movies"])

@app.route("/logs")
def logs():
    return "<br>".join(LOGS)

# ================================
# TELEGRAM
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        log(f"UPDATE: {update}")

        if "message" not in update:
            return "ok"

        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg or "document" in msg:
            data = load_data()
            caption = msg.get("caption", "")

            info = extract(caption)

            if not info:
                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Fehler"
                })
                return "ok"

            for m in data["movies"]:
                if m["title"].lower() == info["title"].lower():
                    return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg.get("video", msg.get("document"))["file_id"],
                "views": 0,
                "timestamp": time.time(),
                "poster": get_poster(info["title"])
            }

            data["movies"].append(entry)
            save_data(data)

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ {info['title']} gespeichert"
            })

        return "ok"

    except Exception as e:
        log(f"ERROR: {e}")
        return "ok"

# ================================
# KEEP ALIVE
# ================================

def keep_alive():
    while True:
        try:
            if os.getenv("WEBHOOK_URL"):
                requests.get(os.getenv("WEBHOOK_URL"))
        except:
            pass
        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# ================================
# START
# ================================

if __name__ == "__main__":
    log("🔥 FINAL UI SYSTEM START")

    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)