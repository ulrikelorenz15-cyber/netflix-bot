# ================================
# 🎬 NETFLIX FINAL SYSTEM (REAL APP MODE)
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"
TMDB_KEY = os.getenv("TMDB_KEY")

USER_STATE = {}

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
# TMDB COVER
# ================================

def get_poster(title):
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_KEY, "query": title}
        ).json()

        if r["results"]:
            return "https://image.tmdb.org/t/p/w500" + r["results"][0]["poster_path"]
    except:
        pass

    return "https://dummyimage.com/300x450/000/fff&text=No+Cover"

# ================================
# PARSER
# ================================

def safe(p, t):
    m = re.search(p, t, re.S)
    return m.group(1).strip() if m else "-"

def extract(text):
    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t:
        return None

    genres = re.findall(r"#(\w+)", text)
    genres = [g for g in genres if not g.isdigit()] or ["Action"]

    return {
        "title": t.group(1),
        "year": t.group(2),
        "rating": safe(r"⭐\s*([0-9.]+)", text),
        "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
        "genre": genres[:2],
        "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
    }

# ================================
# SCORE
# ================================

def score(m):
    return m["views"] * 2 + (5 - (time.time() - m["timestamp"]) / 86400)

# ================================
# USER STATE
# ================================

def update_continue(uid, mid):
    USER_STATE.setdefault(uid, [])

    if mid in USER_STATE[uid]:
        USER_STATE[uid].remove(mid)

    USER_STATE[uid].insert(0, mid)
    USER_STATE[uid] = USER_STATE[uid][:5]

# ================================
# HOME UI
# ================================

@app.route("/")
def home():
    data = load_data()["movies"]
    trending = sorted(data, key=score, reverse=True)[:10]

    return render_template_string("""
    <html>
    <head>
    <style>
    body {background:#141414;color:white;font-family:sans-serif;margin:0}
    .row {display:flex;overflow-x:auto;padding:20px}
    .card {margin-right:10px}
    .card img {width:150px;border-radius:8px}
    </style>
    </head>
    <body>

    <h2 style="padding:20px;">🔥 Trending</h2>

    <div class="row">
    {% for m in trending %}
        <a href="/movie/{{m.id}}">
            <div class="card">
                <img src="{{m.poster}}">
            </div>
        </a>
    {% endfor %}
    </div>

    </body>
    </html>
    """, trending=trending)

# ================================
# DETAIL
# ================================

@app.route("/movie/<mid>")
def movie(mid):
    data = load_data()["movies"]
    m = next((x for x in data if x["id"] == mid), None)

    return render_template_string("""
    <html>
    <head>
    <style>
    body {background:#141414;color:white;font-family:sans-serif;padding:20px}
    img {width:200px;border-radius:10px}
    .btn {background:red;padding:10px 20px;color:white;text-decoration:none;border-radius:5px}
    </style>
    </head>
    <body>

    <img src="{{m.poster}}">
    <h1>{{m.title}} ({{m.year}})</h1>

    <p>⭐ {{m.rating}} • ⏱ {{m.runtime}}</p>
    <p>{{m.genre}}</p>

    <h3>📖 STORY</h3>
    <p>{{m.story}}</p>

    <br>

    <a class="btn" href="/play/{{m.id}}">▶️ Play</a>
    <a class="btn" href="/edit/{{m.id}}">✏️ Edit</a>
    <a class="btn" href="/delete/{{m.id}}">🗑 Delete</a>

    </body>
    </html>
    """, m=m)

# ================================
# PLAY (USER BASED)
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = request.args.get("uid")

    data = load_data()["movies"]
    m = next((x for x in data if x["id"] == mid), None)

    if m and uid:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m["file_id"],
            "caption": f"▶️ {m['title']}"
        })

        m["views"] += 1
        save_data({"movies": data})

    return "▶️ Wird abgespielt..."

# ================================
# EDIT
# ================================

@app.route("/edit/<mid>", methods=["GET","POST"])
def edit(mid):
    data = load_data()
    m = next((x for x in data["movies"] if x["id"] == mid), None)

    if request.method == "POST":
        m["title"] = request.form["title"]
        m["story"] = request.form["story"]
        save_data(data)

    return render_template_string("""
    <form method="post">
        <input name="title" value="{{m.title}}"><br>
        <textarea name="story">{{m.story}}</textarea><br>
        <button>Save</button>
    </form>
    """, m=m)

# ================================
# DELETE
# ================================

@app.route("/delete/<mid>")
def delete(mid):
    data = load_data()
    data["movies"] = [m for m in data["movies"] if m["id"] != mid]
    save_data(data)
    return "Deleted"

# ================================
# WEBHOOK
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg:
            data = load_data()
            info = extract(msg.get("caption",""))

            if not info:
                return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg["video"]["file_id"],
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

# ================================
# START
# ================================

if __name__ == "__main__":
    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)