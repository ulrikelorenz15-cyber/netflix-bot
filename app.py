# ================================
# 🎬 NETFLIX HYBRID SYSTEM (FINAL)
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

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
        title TEXT,
        type TEXT,
        season INTEGER,
        episode INTEGER,
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
# SAVE FROM TELEGRAM
# ================================

def save(msg):
    global LAST_COVER
    chat_id = msg["chat"]["id"]

    # Cover speichern
    if "photo" in msg:
        LAST_COVER[chat_id] = msg["photo"][-1]["file_id"]
        return

    if "video" not in msg:
        return

    video = msg["video"]
    info = extract(msg.get("caption",""))

    if not info:
        return

    content_type = "series" if info["season"] else "movie"

    # ❗ wichtig: Telegram Cover NICHT direkt anzeigen
    poster = f"https://dummyimage.com/300x450/000/fff&text={info['title'].replace(' ','+')}"

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO content VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        info["title"],
        content_type,
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
# API
# ================================

@app.route("/api/content")
def api():
    con = db()
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM content").fetchall()
    con.close()

    data = [{
        "id": r[0],
        "title": r[1],
        "type": r[2],
        "season": r[3],
        "episode": r[4],
        "story": r[5],
        "file_id": r[6],
        "poster": r[7],
        "views": r[8]
    } for r in rows]

    return jsonify(data)

# ================================
# PLAY
# ================================

@app.route("/play/<id>")
def play(id):
    uid = request.args.get("uid")

    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM content WHERE id=?", (id,)).fetchone()

    if m and uid:
        cur.execute("UPDATE content SET views=views+1 WHERE id=?", (id,))
        con.commit()

        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m[6],
            "caption": m[1]
        })

    con.close()
    return "OK"

# ================================
# WEB APP (ECHTES UI)
# ================================

@app.route("/")
def home():
    return render_template_string("""
    <html>
    <meta name="viewport" content="width=device-width">

    <style>
    body {background:#141414;color:white;margin:0;font-family:sans-serif}

    .hero {
        height:70vh;
        display:flex;
        align-items:end;
        padding:30px;
        background-size:cover;
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
        width:160px;
        border-radius:10px;
    }

    .card:hover {
        transform:scale(1.2);
    }

    .overlay {
        position:absolute;
        bottom:0;
        background:rgba(0,0,0,0.8);
        width:100%;
        opacity:0;
    }

    .card:hover .overlay {
        opacity:1;
    }

    </style>

    <body>

    <div id="hero" class="hero"></div>

    <h2 style="padding-left:20px;">🔥 Trending</h2>
    <div id="row" class="row"></div>

    <script>
    let uid = prompt("Telegram ID:");

    fetch("/api/content")
    .then(r=>r.json())
    .then(data=>{

        if(data.length>0){
            document.getElementById("hero").style.backgroundImage =
                "url("+data[0].poster+")";
        }

        let row = document.getElementById("row");

        data.forEach(m=>{
            let card = document.createElement("div");
            card.className="card";

            card.innerHTML = `
                <img src="${m.poster}">
                <div class="overlay">${m.title}</div>
            `;

            card.onclick=()=>{
                window.location="/play/"+m.id+"?uid="+uid;
            }

            row.appendChild(card);
        });
    });
    </script>

    </body>
    </html>
    """)

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
    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))