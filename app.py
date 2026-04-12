# ================================
# 🎬 FINAL ULTRA STABLE BACKEND
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TOKEN = os.getenv("BOT_TOKEN")
TMDB_KEY = os.getenv("TMDB_KEY")
URL = f"https://api.telegram.org/bot{TOKEN}"

DB = "netflix.db"

# ================================
# DB INIT (AUTO FIX)
# ================================

def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cur = con.cursor()

    # neue Struktur (mit cover + category)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        id TEXT,
        title TEXT,
        story TEXT,
        file_id TEXT,
        cover TEXT,
        category TEXT,
        progress INTEGER
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# COVER (TMDB)
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

    return "https://placehold.co/300x450?text=" + title.replace(" ","+")

# ================================
# PARSER (CLEAN)
# ================================

def extract_data(caption):
    if not caption:
        return "Film", "-", "General"

    # 🎬 Titel
    title_match = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title_match.group(1) if title_match else caption.split("\n")[0]

    # 📖 Story
    story_match = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption, re.S)
    story = story_match.group(1).strip() if story_match else "-"

    # 🏷 Kategorie
    tags = re.findall(r"#(\w+)", caption)
    category = tags[0] if tags else "General"

    return title.strip(), story.strip(), category

# ================================
# SAVE TELEGRAM
# ================================

def save(msg):
    if "video" not in msg:
        return

    try:
        title, story, category = extract_data(msg.get("caption",""))
        cover = get_cover(title)

        con = db()
        cur = con.cursor()

        cur.execute("""
        INSERT INTO movies VALUES(?,?,?,?,?,?,?)
        """, (
            str(int(time.time())),
            title,
            story,
            msg["video"]["file_id"],
            cover,
            category,
            0
        ))

        con.commit()
        con.close()

        print("✅ Saved:", title)

    except Exception as e:
        print("❌ SAVE ERROR:", e)

# ================================
# TELEGRAM FILE
# ================================

def get_file(file_id):
    r = requests.get(f"{URL}/getFile?file_id={file_id}").json()
    path = r["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TOKEN}/{path}"

# ================================
# STREAM
# ================================

@app.route("/stream/<id>")
def stream(id):
    try:
        con = db()
        cur = con.cursor()

        m = cur.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
       