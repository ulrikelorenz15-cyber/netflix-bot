# ================================
# 🎬 ULTRA NETFLIX SYSTEM (FINAL)
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "ultra_netflix"

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

DB = "netflix.db"

# ================================
# DB
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

    con.commit()
    con.close()

init_db()

# ================================
# TMDB COVER
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
# SAVE MOVIE
# ================================

def save_movie(msg):
    caption = msg.get("caption","")
    video = msg.get("video") or msg.get("document")

    parsed = extract(caption)
    if not parsed:
        return

    title, story = parsed

    poster = get_tmdb(title)
    if not poster:
        poster = "https://dummyimage.com/300x450/000/fff&text=" + title.replace(" ","+")

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
# GET MOVIES
# ================================

def get_movies():
    con = db()
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM movies").fetchall()
    con.close()

    return [{
        "id": r[0],
        "title": r[1],
        "story": r[2],
        "file_id": r[3],
        "poster": r[4],
        "views": r[5],
        "timestamp": r[6]
    } for r in rows]

# ================================
# TRENDING
# ================================

def trending(movies):
    return sorted(
        movies,
        key=lambda m: m["views"] + (10 - (time.time() - m["timestamp"]) / 86400),
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

    return """
    <h2 style="color:white;background:#141414;padding:20px">Login</h2>
    <form method="post" style="padding:20px">
        Telegram ID:<br>
        <input name="uid"><br><br>
        <button>Login</button>
    </form>
    """

# ================================
# HOME (ULTRA UI)
# ================================

@app.route("/")
def home():
    if not session.get("uid"):
        return redirect("/login")

    movies = get_movies()
    top = trending(movies)

    hero = top[0] if top else None

    return render_template_string("""
    <html>
    <meta name="viewport" content="width=device-width">

    <style>
    body {background:#141414;color:white;margin:0;font-family:sans-serif}

    .nav {
        position:fixed;
        width:100%;
        padding:15px;
        background:linear-gradient(to bottom, rgba(0,0,0,0.9), transparent);
        z-index:10;
        display:flex;
        justify-content:space-between;
    }

    .nav a {
        color:white;
        text-decoration:none;
        margin-left:15px;
    }

    .hero {
        height:75vh;
        background-size:cover;
        display:flex;
        align-items:flex-end;
        padding:30px;
    }

    .hero::after {
        content:"";
        position:absolute;
        width:100%;
        height:200px;
        bottom:0;
        background:linear-gradient(to top,#141414,transparent);
    }

    .row {
        display:flex;
        overflow-x:auto;
        padding:20px;
    }

    .card {
        margin-right:10px;
        transition:0.3s;
        position:relative;
    }

    .card img {
        width:150px;
        border-radius:10px;
    }

    .card:hover {
        transform:scale(1.2);
    }

    .overlay {
        position:absolute;
        bottom:0;
        width:100%;
        background:rgba(0,0,0,0.7);
        font-size:12px;
        padding:5px;
        opacity:0;
    }

    .card:hover .overlay {
        opacity:1;
    }

    h2 {padding-left:20px}
    </style>

    <div class="nav">
        <div>🎬 NETFLIX</div>
        <div>
            <a href="/admin">Admin</a>
        </div>
    </div>

    {% if hero %}
    <div class="hero" style="background-image:url('{{hero.poster}}')">
        <h1>{{hero.title}}</h1>
    </div>
    {% endif %}

    <h2>🔥 Trending</h2>
    <div class="row">
    {% for m in top %}
        <a href="/play/{{m.id}}">
            <div class="card">
                <img src="{{m.poster}}">
                <div class="overlay">{{m.title}}</div>
            </div>
        </a>
    {% endfor %}
    </div>

    <h2>🎬 Alle Filme</h2>
    <div class="row">
    {% for m in movies %}
        <a href="/play/{{m.id}}">
            <div class="card">
                <img src="{{m.poster}}">
                <div class="overlay">{{m.title}}</div>
            </div>
        </a>
    {% endfor %}
    </div>

    """, movies=movies, top=top, hero=hero)

# ================================
# PLAY
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = session.get("uid")

    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()

    if m and uid:
        cur.execute("UPDATE movies SET views=views+1 WHERE id=?", (mid,))
        con.commit()

        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m[3],
            "caption": f"▶️ {m[1]}"
        })

    con.close()
    return redirect("/")

# ================================
# ADMIN
# ================================

@app.route("/admin")
def admin():
    movies = get_movies()

    return render_template_string("""
    <h1>Admin Panel</h1>

    {% for m in movies %}
        <div>
            <b>{{m.title}}</b><br>
            <img src="{{m.poster}}" width="120"><br>
            <a href="/edit/{{m.id}}">Edit</a>
            <a href="/delete/{{m.id}}">Delete</a>
        </div><hr>
    {% endfor %}
    """, movies=movies)

# ================================
# EDIT
# ================================

@app.route("/edit/<mid>", methods=["GET","POST"])
def edit(mid):
    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()

    if request.method == "POST":
        cur.execute("""
        UPDATE movies SET title=?, poster=?, story=? WHERE id=?
        """, (
            request.form["title"],
            request.form["poster"],
            request.form["story"],
            mid
        ))
        con.commit()
        con.close()
        return redirect("/admin")

    con.close()

    return render_template_string("""
    <form method="post">
        Title:<br><input name="title" value="{{m[1]}}"><br><br>
        Poster:<br><input name="poster" value="{{m[4]}}"><br><br>
        Story:<br><textarea name="story">{{m[2]}}</textarea><br><br>
        <button>Save</button>
    </form>
    """, m=m)

# ================================
# DELETE
# ================================

@app.route("/delete/<mid>")
def delete(mid):
    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM movies WHERE id=?", (mid,))
    con.commit()
    con.close()

    return redirect("/admin")

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