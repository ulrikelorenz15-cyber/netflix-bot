# ================================
# 🎬 NETFLIX FINAL SYSTEM (REAL UI + TMDB)
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

TMDB_KEY = os.getenv("TMDB_KEY")

USER_STATE = {}
LOGS = []

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
    except:
        pass
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# TMDB COVER
# ================================

def get_tmdb_poster(title):
    try:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={title}"
        r = requests.get(url).json()

        if r["results"]:
            return "https://image.tmdb.org/t/p/w500" + r["results"][0]["poster_path"]
    except:
        pass

    return "https://dummyimage.com/300x450/000/fff&text=No+Cover"

# ================================
# SAFE REGEX
# ================================

def safe(pattern, text):
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else "-"

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

        genres = [g for g in genres if not g.isdigit()]

        if not genres:
            genres = ["Action"]

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
# SCORE (TRENDING)
# ================================

def score(m):
    return m["views"] * 2 + (5 - (time.time() - m["timestamp"]) / 86400)

# ================================
# WEB UI (NETFLIX)
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
    body {background:#141414;color:white;font-family:sans-serif;margin:0}
    .hero {height:300px;background-size:cover;display:flex;align-items:flex-end;padding:20px;font-size:30px;font-weight:bold}
    .row {display:flex;overflow-x:auto;padding:10px 20px}
    .card {margin-right:10px;transition:0.3s}
    .card img {width:140px;border-radius:8px}
    .card:hover {transform:scale(1.3);z-index:2}
    h2 {margin-left:20px}
    </style>
    </head>
    <body>

    {% if trending %}
    <div class="hero" style="background-image:url('{{trending[0].poster}}')">
        {{trending[0].title}}
    </div>
    {% endif %}

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
# TELEGRAM WEBHOOK
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
                "poster": get_tmdb_poster(info["title"])
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
    log("🔥 FINAL NETFLIX SYSTEM START")

    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)