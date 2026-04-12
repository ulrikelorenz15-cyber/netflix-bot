# ================================
# 🎬 NETFLIX FINAL GOD UI SYSTEM
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "netflix_god_ui"

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DB = "netflix.db"
LAST_COVER = {}

# ================================
# DB
# ================================

def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS content(
        id TEXT,
        type TEXT,
        title TEXT,
        season INTEGER,
        episode INTEGER,
        story TEXT,
        file_id TEXT,
        poster TEXT,
        progress INTEGER DEFAULT 0,
        timestamp REAL
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# PARSER
# ================================

def extract(text):
    title = re.search(r"🎬\s*(.*?)\s*\(", text)
    season = re.search(r"S(\d+)", text)
    episode = re.search(r"E(\d+)", text)

    story = "-"
    s = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S)
    if s:
        story = s.group(1)

    return {
        "title": title.group(1) if title else "Unknown",
        "season": int(season.group(1)) if season else None,
        "episode": int(episode.group(1)) if episode else None,
        "story": story
    }

# ================================
# SAVE CONTENT
# ================================

def save_content(msg):
    global LAST_COVER
    chat_id = msg["chat"]["id"]

    if "photo" in msg:
        LAST_COVER[chat_id] = msg["photo"][-1]["file_id"]
        return

    if "video" not in msg and "document" not in msg:
        return

    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption","")

    info = extract(caption)
    content_type = "series" if info["season"] else "movie"

    poster = LAST_COVER.get(chat_id, "https://dummyimage.com/300x450/000/fff")

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO content VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        content_type,
        info["title"],
        info["season"],
        info["episode"],
        info["story"],
        video["file_id"],
        poster,
        0,
        time.time()
    ))

    con.commit()
    con.close()

# ================================
# GET DATA
# ================================

def get_all():
    con = db()
    cur = con.cursor()
    rows = cur.execute("SELECT * FROM content").fetchall()
    con.close()

    return [{
        "id": r[0],
        "type": r[1],
        "title": r[2],
        "season": r[3],
        "episode": r[4],
        "story": r[5],
        "file_id": r[6],
        "poster": r[7],
        "progress": r[8]
    } for r in rows]

# ================================
# LOGIN
# ================================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["uid"] = request.form["uid"]
        return redirect("/")
    return "<form method='post'>ID:<input name='uid'><button>Login</button></form>"

# ================================
# HOME (NETFLIX UI)
# ================================

@app.route("/")
def home():
    if not session.get("uid"):
        return redirect("/login")

    data = get_all()

    movies = [x for x in data if x["type"]=="movie"]
    series_titles = list(set([x["title"] for x in data if x["type"]=="series"]))

    hero = movies[0] if movies else None

    return render_template_string("""
    <html>
    <meta name="viewport" content="width=device-width">

    <style>
    body {background:#141414;color:white;margin:0;font-family:sans-serif}

    .hero {
        height:70vh;
        background-size:cover;
        display:flex;
        align-items:flex-end;
        padding:20px;
    }

    .row {display:flex;overflow-x:auto;padding:15px}

    .card {position:relative;margin-right:10px}
    .card img {width:150px;border-radius:10px}

    .card:hover {transform:scale(1.1)}

    .overlay {
        position:absolute;
        bottom:0;
        width:100%;
        background:rgba(0,0,0,0.7);
        font-size:12px;
    }

    .progress {
        height:4px;
        background:red;
        width:{{m.progress}}%;
    }
    </style>

    {% if hero %}
    <div class="hero" style="background-image:url('{{hero.poster}}')">
        <h1>{{hero.title}}</h1>
    </div>
    {% endif %}

    <h2>🎬 Filme</h2>
    <div class="row">
    {% for m in movies %}
        <a href="/details/{{m.id}}">
            <div class="card">
                <img src="{{m.poster}}">
                <div class="overlay">{{m.title}}</div>
                <div class="progress"></div>
            </div>
        </a>
    {% endfor %}
    </div>

    <h2>📺 Serien</h2>
    <div class="row">
    {% for s in series %}
        <a href="/series/{{s}}">{{s}}</a>
    {% endfor %}
    </div>
    """, movies=movies, series=series_titles, hero=hero)

# ================================
# DETAILS
# ================================

@app.route("/details/<id>")
def details(id):
    data = get_all()
    m = next(x for x in data if x["id"]==id)

    return render_template_string("""
    <h1>{{m.title}}</h1>
    <img src="{{m.poster}}" width="200">
    <p>{{m.story}}</p>

    <a href="/play/{{m.id}}">▶️ Play</a>
    """, m=m)

# ================================
# SERIES VIEW
# ================================

@app.route("/series/<title>")
def series(title):
    data = get_all()
    eps = [x for x in data if x["title"]==title]

    return render_template_string("""
    <h1>{{title}}</h1>

    {% for e in eps %}
        <div>
            S{{e.season}}E{{e.episode}}
            <a href="/play/{{e.id}}">▶️</a>
        </div>
    {% endfor %}
    """, eps=eps, title=title)

# ================================
# PLAY + AUTO NEXT
# ================================

@app.route("/play/<id>")
def play(id):
    uid = session.get("uid")

    data = get_all()
    current = next(x for x in data if x["id"]==id)

    # Send video
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": uid,
        "video": current["file_id"],
        "caption": current["title"]
    })

    # AUTO NEXT
    if current["type"] == "series":
        next_ep = next((x for x in data
            if x["title"] == current["title"]
            and x["season"] == current["season"]
            and x["episode"] == current["episode"] + 1), None)

        if next_ep:
            requests.post(f"{URL}/sendMessage", json={
                "chat_id": uid,
                "text": f"➡️ Nächste Folge verfügbar: S{next_ep['season']}E{next_ep['episode']}"
            })

    return redirect("/")

# ================================
# WEBHOOK
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        save_content(update["message"])

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))