# ================================
# 🎬 NETFLIX GOD MODE SYSTEM
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "netflix_god"

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

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
        season TEXT,
        episode TEXT,
        story TEXT,
        file_id TEXT,
        poster TEXT,
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
        "season": season.group(1) if season else None,
        "episode": episode.group(1) if episode else None,
        "story": story
    }

# ================================
# SAVE
# ================================

def save_content(msg):
    global LAST_COVER

    chat_id = msg["chat"]["id"]

    # COVER SPEICHERN
    if "photo" in msg:
        LAST_COVER[chat_id] = msg["photo"][-1]["file_id"]
        return

    if "video" not in msg and "document" not in msg:
        return

    video = msg.get("video") or msg.get("document")
    caption = msg.get("caption","")

    info = extract(caption)

    content_type = "series" if info["season"] else "movie"

    poster = LAST_COVER.get(chat_id)

    if not poster:
        poster = "https://dummyimage.com/300x450/000/fff&text=" + info["title"]

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO content VALUES(?,?,?,?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        content_type,
        info["title"],
        info["season"],
        info["episode"],
        info["story"],
        video["file_id"],
        poster,
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
        "poster": r[7]
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
# HOME
# ================================

@app.route("/")
def home():
    if not session.get("uid"):
        return redirect("/login")

    data = get_all()

    movies = [x for x in data if x["type"]=="movie"]
    series = list(set([x["title"] for x in data if x["type"]=="series"]))

    return render_template_string("""
    <style>
    body {background:#141414;color:white;font-family:sans-serif}
    .row {display:flex;overflow-x:auto}
    img {width:140px;margin:5px;border-radius:10px}
    </style>

    <h2>🎬 Filme</h2>
    <div class="row">
    {% for m in movies %}
        <a href="/details/{{m.id}}"><img src="{{m.poster}}"></a>
    {% endfor %}
    </div>

    <h2>📺 Serien</h2>
    <div class="row">
    {% for s in series %}
        <a href="/series/{{s}}">{{s}}</a><br>
    {% endfor %}
    </div>
    """, movies=movies, series=series)

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
            S{{e.season}} E{{e.episode}}
            <a href="/play/{{e.id}}">▶️</a>
        </div>
    {% endfor %}
    """, eps=eps, title=title)

# ================================
# PLAY
# ================================

@app.route("/play/<id>")
def play(id):
    uid = session.get("uid")

    data = get_all()
    m = next(x for x in data if x["id"]==id)

    requests.post(f"{URL}/sendVideo", json={
        "chat_id": uid,
        "video": m["file_id"],
        "caption": m["title"]
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