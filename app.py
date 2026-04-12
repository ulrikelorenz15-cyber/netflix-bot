# ================================
# 🎬 NETFLIX SYSTEM (AUTO COVER PERFECT)
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify, render_template_string, redirect
from difflib import get_close_matches

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"
TMDB_KEY = os.getenv("TMDB_KEY")

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": [], "series": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(arr):
    return str(len(arr) + 1).zfill(4)

# ================================
# 🧠 AUTO COVER SYSTEM
# ================================

def clean_title(title):
    title = title.replace(".", " ")
    blacklist = ["1080p","720p","bluray","x264","x265","webdl"]
    return " ".join([w for w in title.split() if w.lower() not in blacklist])

def search_tmdb(title, is_series=False):
    try:
        title = clean_title(title)

        endpoint = "tv" if is_series else "movie"

        r = requests.get(
            f"https://api.themoviedb.org/3/search/{endpoint}",
            params={"api_key": TMDB_KEY, "query": title}
        ).json()

        if r["results"]:
            return r["results"][0]["poster_path"]

    except:
        pass

    return None

def get_best_poster(title, is_series=False):
    poster = search_tmdb(title, is_series)

    if poster:
        return "https://image.tmdb.org/t/p/w500" + poster

    # 🔥 Fallback 1: shorter title
    short = " ".join(title.split()[:2])
    poster = search_tmdb(short, is_series)

    if poster:
        return "https://image.tmdb.org/t/p/w500" + poster

    # 🔥 Fallback 2: default
    return "https://dummyimage.com/300x450/000/fff&text=" + title.replace(" ","+")

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

    return {
        "title": t.group(1),
        "year": t.group(2),
        "rating": safe(r"⭐\s*([0-9.]+)", text),
        "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
        "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
    }

# ================================
# UI
# ================================

@app.route("/")
def home():
    data = load_data()

    return render_template_string("""
    <html>
    <style>
    body {background:#141414;color:white;font-family:sans-serif}
    .row {display:flex;overflow-x:auto;padding:20px}
    img {width:150px;border-radius:8px;margin-right:10px}
    </style>

    <h2>🎬 Filme</h2>
    <div class="row">
    {% for m in data.movies %}
        <a href="/movie/{{m.id}}">
            <img src="{{m.poster}}">
        </a>
    {% endfor %}
    </div>

    <h2>📺 Serien</h2>
    <div class="row">
    {% for s in data.series %}
        <img src="{{s.poster}}">
    {% endfor %}
    </div>
    """, data=data)

# ================================
# DETAIL
# ================================

@app.route("/movie/<mid>")
def movie(mid):
    data = load_data()
    m = next(x for x in data["movies"] if x["id"] == mid)

    return render_template_string("""
    <h1>{{m.title}}</h1>
    <img src="{{m.poster}}">
    <p>{{m.story}}</p>

    <a href="/play/{{m.id}}">▶️ Play</a>
    <a href="/edit/{{m.id}}">✏️ Edit</a>
    """, m=m)

# ================================
# EDIT (COVER MANUELL)
# ================================

@app.route("/edit/<mid>", methods=["GET","POST"])
def edit(mid):
    data = load_data()
    m = next(x for x in data["movies"] if x["id"] == mid)

    if request.method == "POST":
        m["title"] = request.form["title"]
        m["poster"] = request.form["poster"] or get_best_poster(m["title"])
        m["story"] = request.form["story"]
        save_data(data)
        return redirect("/")

    return render_template_string("""
    <form method="post">
        Title: <input name="title" value="{{m.title}}"><br>
        Poster URL: <input name="poster" value="{{m.poster}}"><br>
        Story: <textarea name="story">{{m.story}}</textarea><br>
        <button>Save</button>
    </form>
    """, m=m)

# ================================
# PLAY
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = request.args.get("uid")
    data = load_data()

    m = next(x for x in data["movies"] if x["id"] == mid)

    if uid:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m["file_id"],
            "caption": f"▶️ {m['title']}"
        })

    return "Playing..."

# ================================
# WEBHOOK (AUTO COVER!)
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
                "id": get_id(data["movies"]),
                **info,
                "file_id": msg["video"]["file_id"],
                "poster": get_best_poster(info["title"])  # 🔥 AUTO COVER
            }

            data["movies"].append(entry)
            save_data(data)

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"🎬 {info['title']} + Cover geladen ✅"
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