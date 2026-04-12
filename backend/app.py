# ================================
# 🎬 FULL STACK ELITE BACKEND
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, jsonify, Response, session
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv("SECRET_KEY","secret")

TOKEN = os.getenv("BOT_TOKEN")
TMDB_KEY = os.getenv("TMDB_KEY")
URL = f"https://api.telegram.org/bot{TOKEN}"

DB = "netflix.db"

def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS movies(id TEXT, title TEXT, story TEXT, file_id TEXT, cover TEXT, category TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS progress(user TEXT, movie_id TEXT, progress INTEGER)")

    con.commit()
    con.close()

init_db()

# ================================
# PARSER + COVER
# ================================

def get_cover(title):
    try:
        if TMDB_KEY:
            r = requests.get(
                "https://api.themoviedb.org/3/search/movie",
                params={"api_key": TMDB_KEY, "query": title}
            ).json()
            if r.get("results"):
                path = r["results"][0].get("poster_path")
                if path:
                    return "https://image.tmdb.org/t/p/w500" + path
    except:
        pass
    return "https://placehold.co/300x450?text=" + title

def extract_data(caption):
    title = re.search(r"🎬\s*(.*?)\s*\(", caption or "")
    title = title.group(1) if title else "Film"

    story = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption or "", re.S)
    story = story.group(1).strip() if story else "-"

    tags = re.findall(r"#([A-Za-z]+)", caption or "")
    category = tags[0] if tags else "General"

    return title, story, category

# ================================
# TELEGRAM SAVE
# ================================

def save(msg):
    if "video" not in msg:
        return

    title, story, category = extract_data(msg.get("caption",""))
    cover = get_cover(title)

    con = db()
    cur = con.cursor()

    cur.execute("INSERT INTO movies VALUES(?,?,?,?,?,?)", (
        str(int(time.time())),
        title,
        story,
        msg["video"]["file_id"],
        cover,
        category
    ))

    con.commit()
    con.close()

# ================================
# STREAM
# ================================

def get_file(file_id):
    r = requests.get(f"{URL}/getFile?file_id={file_id}").json()
    path = r["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TOKEN}/{path}"

@app.route("/stream/<id>")
def stream(id):
    con = db()
    cur = con.cursor()
    m = cur.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
    con.close()

    url = get_file(m[3])

    def generate():
        with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(1024*1024):
                yield chunk

    return Response(generate(), content_type="video/mp4")

# ================================
# AUTH
# ================================

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    con = db()
    cur = con.cursor()

    user = cur.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (data["username"], data["password"])
    ).fetchone()

    con.close()

    if user:
        session["user"] = data["username"]
        return {"status":"ok"}

    return {"status":"fail"}

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    con = db()
    cur = con.cursor()

    cur.execute("INSERT INTO users(username,password) VALUES(?,?)",
                (data["username"], data["password"]))

    con.commit()
    con.close()

    return {"status":"ok"}

# ================================
# API
# ================================

@app.route("/movies")
def movies():
    con = db()
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM movies").fetchall()
    con.close()

    return jsonify([
        {
            "id": r[0],
            "title": r[1],
            "story": r[2],
            "cover": r[4],
            "category": r[5]
        } for r in rows
    ])

# ================================
# WEBHOOK
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        save(update["message"])
    return "ok"

# ================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))