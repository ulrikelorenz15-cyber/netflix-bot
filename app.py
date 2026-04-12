# ================================
# 🎬 NETFLIX CLOUD SYSTEM (FINAL)
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "netflix_cloud"

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

DB = "netflix.db"

# ================================
# DB INIT
# ================================

def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        id TEXT,
        title TEXT,
        story TEXT,
        file_id TEXT,
        poster TEXT,
        views INTEGER,
        timestamp REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        uid TEXT,
        history TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# AUTO COVER (TMDB)
# ================================

def get_tmdb(title):
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_KEY, "query": title}
        ).json()

        if r["results"]:
            return "https://image.tmdb.org/t/p/w500" + r["results"][0]["poster_path"]
    except:
        pass

    return None

# ================================
# PARSER
# ================================

def extract(text):
    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t:
        return None

    story = "-"
    s = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S)
    if s:
        story = s.group(1)

    return t.group(1), story

# ================================
# SAVE MOVIE (SMART COVER)
# ================================

def save_movie(msg):
    caption = msg.get("caption","")
    video = msg.get("video") or msg.get("document")

    parsed = extract(caption)
    if not parsed:
        return

    title, story = parsed

    # 🔥 PRIORITY COVER SYSTEM
    poster = None

    # 1️⃣ TELEGRAM THUMB
    if video.get("thumb"):
        poster = video["thumb"]["file_id"]

    # 2️⃣ PHOTO IN MESSAGE
    if "photo" in msg:
        poster = msg["photo"][-1]["file_id"]

    # 3️⃣ TMDB
    if not poster:
        poster = get_tmdb(title)

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        story,
        video["file_id"],
        poster,
        0,
        time.time()
    ))

    con.commit()
    con.close()

# ================================
# TRENDING
# ================================

def get_movies():
    con = db()
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM movies").fetchall()
    con.close()

    movies = []
    for r in rows:
        movies.append({
            "id": r[0],
            "title": r[1],
            "story": r[2],
            "file_id": r[3],
            "poster": r[4],
            "views": r[5],
            "timestamp": r[6]
        })

    return movies

def trending(movies):
    return sorted(
        movies,
        key=lambda m: m["views"] + (10 - (time.time()-m["timestamp"])/86400),
        reverse=True
    )[:10]

# ================================
# LOGIN
# ================================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        session["uid"] = request.form["uid"]
        return redirect("/")
    return "<form method='post'>Telegram ID:<input name='uid'><button>Login</button></form>"

# ================================
# HOME
# ================================

@app.route("/")
def home():
    uid = session.get("uid")
    if not uid:
        return redirect("/login")

    movies = get_movies()
    top = trending(movies)

    hero = top[0] if top else None

    return render_template_string("""
    <html>
    <style>
    body {background:#141414;color:white}
    .row {display:flex;overflow-x:auto}
    img {width:140px;margin:5px;border-radius:8px}
    </style>

    {% if hero %}
    <div style="height:60vh;background:url('{{hero.poster}}');background-size:cover">
        <h1>{{hero.title}}</h1>
    </div>
    {% endif %}

    <h3>🔥 Trending</h3>
    <div class="row">
    {% for m in top %}
        <a href="/play/{{m.id}}"><img src="{{m.poster}}"></a>
    {% endfor %}
    </div>

    """, top=top, hero=hero)

# ================================
# PLAY
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = session.get("uid")

    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()

    if m:
        cur.execute("UPDATE movies SET views=views+1 WHERE id=?", (mid,))
        con.commit()

        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m[3],
            "caption": m[1]
        })

    con.close()
    return redirect("/")

# ================================
# WEBHOOK
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]

        if "video" in msg or "document" in msg:
            save_movie(msg)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)