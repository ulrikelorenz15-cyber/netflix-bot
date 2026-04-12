# ================================
# 🎬 NETFLIX ULTIMATE SYSTEM
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify, render_template_string, redirect

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"
TMDB_KEY = os.getenv("TMDB_KEY")

USER_PROGRESS = {}

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
# PARSER (FILM)
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
# HOME UI
# ================================

@app.route("/")
def home():
    data = load_data()

    return render_template_string("""
    <html>
    <head>
    <style>
    body {background:#141414;color:white;font-family:sans-serif;margin:0}
    .row {display:flex;overflow-x:auto;padding:20px}
    .card img {width:150px;border-radius:8px}
    </style>
    </head>
    <body>

    <h2 style="padding:20px;">🎬 Filme</h2>
    <div class="row">
    {% for m in data.movies %}
        <a href="/movie/{{m.id}}">
            <img src="{{m.poster}}">
        </a>
    {% endfor %}
    </div>

    <h2 style="padding:20px;">📺 Serien</h2>
    <div class="row">
    {% for s in data.series %}
        <a href="/series/{{s.id}}">
            <img src="{{s.poster}}">
        </a>
    {% endfor %}
    </div>

    </body>
    </html>
    """, data=data)

# ================================
# FILM DETAIL
# ================================

@app.route("/movie/<mid>")
def movie(mid):
    data = load_data()
    m = next((x for x in data["movies"] if x["id"] == mid), None)

    return render_template_string("""
    <h1>{{m.title}}</h1>
    <img src="{{m.poster}}">
    <p>{{m.story}}</p>

    <a href="/play/movie/{{m.id}}">▶️ Play</a>
    <a href="/edit/movie/{{m.id}}">✏️ Edit</a>
    """, m=m)

# ================================
# SERIES DETAIL
# ================================

@app.route("/series/<sid>")
def series(sid):
    data = load_data()
    s = next((x for x in data["series"] if x["id"] == sid), None)

    return render_template_string("""
    <h1>{{s.title}}</h1>
    <img src="{{s.poster}}">

    {% for season in s.seasons %}
        <h3>Season {{season.number}}</h3>

        {% for ep in season.episodes %}
            <div>
                Episode {{ep.number}}
                <a href="/play/series/{{s.id}}/{{season.number}}/{{ep.number}}">
                    ▶️ Play
                </a>
            </div>
        {% endfor %}
    {% endfor %}

    <a href="/edit/series/{{s.id}}">✏️ Edit</a>
    """, s=s)

# ================================
# PLAY FILM
# ================================

@app.route("/play/movie/<mid>")
def play_movie(mid):
    uid = request.args.get("uid")
    data = load_data()

    m = next((x for x in data["movies"] if x["id"] == mid), None)

    if m and uid:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m["file_id"],
            "caption": f"▶️ {m['title']}"
        })

    return "Playing..."

# ================================
# PLAY SERIES (AUTO NEXT)
# ================================

@app.route("/play/series/<sid>/<season>/<episode>")
def play_series(sid, season, episode):
    uid = request.args.get("uid")
    data = load_data()

    s = next((x for x in data["series"] if x["id"] == sid), None)

    season = int(season)
    episode = int(episode)

    ep = s["seasons"][season-1]["episodes"][episode-1]

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": uid,
        "video": ep["file_id"],
        "caption": f"▶️ {s['title']} S{season}E{episode}"
    })

    # SAVE PROGRESS
    USER_PROGRESS[uid] = (sid, season, episode)

    # AUTO NEXT
    try:
        next_ep = s["seasons"][season-1]["episodes"][episode]
        requests.post(f"{URL}/sendMessage", json={
            "chat_id": uid,
            "text": f"➡️ Next Episode verfügbar"
        })
    except:
        pass

    return "Playing..."

# ================================
# EDIT (MIT COVER!)
# ================================

@app.route("/edit/<type>/<id>", methods=["GET","POST"])
def edit(type, id):
    data = load_data()

    arr = data[type+"s"]
    item = next((x for x in arr if x["id"] == id), None)

    if request.method == "POST":
        item["title"] = request.form["title"]
        item["poster"] = request.form["poster"]  # 🔥 COVER EDIT
        item["story"] = request.form["story"]
        save_data(data)
        return redirect("/")

    return render_template_string("""
    <form method="post">
        Title: <input name="title" value="{{item.title}}"><br>
        Poster URL: <input name="poster" value="{{item.poster}}"><br>
        Story: <textarea name="story">{{item.story}}</textarea><br>
        <button>Save</button>
    </form>
    """, item=item)

# ================================
# WEBHOOK (UPLOAD)
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