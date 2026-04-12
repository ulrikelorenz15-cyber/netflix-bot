# ================================
# 🎬 FINAL BACKEND (CLEAN VERSION)
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
URL = f"https://api.telegram.org/bot{TOKEN}"

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
        progress INTEGER
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# 🎯 FINAL PARSER (CLEAN)
# ================================

def extract_data(caption):
    if not caption:
        return "Film", "-"

    # 🎬 Titel sauber
    title_match = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title_match.group(1) if title_match else caption.split("\n")[0]

    # 📖 Story sauber
    story = "-"
    story_match = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption, re.S)

    if story_match:
        story = story_match.group(1).strip()

    return title.strip(), story.strip()

# ================================
# SAVE TELEGRAM
# ================================

def save(msg):
    if "video" not in msg:
        return

    title, story = extract_data(msg.get("caption",""))

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        story,
        msg["video"]["file_id"],
        0
    ))

    con.commit()
    con.close()

    print("✅ Saved:", title)

# ================================
# TELEGRAM FILE URL
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
    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
    con.close()

    if not m:
        return "Not found"

    file_url = get_file(m[3])

    def generate():
        with requests.get(file_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk

    return Response(generate(), content_type="video/mp4")

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
            "progress": r[4]
        } for r in rows
    ])

# ================================
# PROGRESS
# ================================

@app.route("/progress", methods=["POST"])
def progress():
    data = request.json

    con = db()
    cur = con.cursor()

    cur.execute("UPDATE movies SET progress=? WHERE id=?", (
        int(data["progress"]),
        data["id"]
    ))

    con.commit()
    con.close()

    return "ok"

# ================================
# ROOT
# ================================

@app.route("/")
def root():
    return "✅ Backend läuft"

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
# START
# ================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))