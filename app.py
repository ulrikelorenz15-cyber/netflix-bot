# ================================
# 🎬 NETFLIX CLEAN WORKING SYSTEM
# ================================

import os
import sqlite3
import requests
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

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
        poster TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# SAVE FROM TELEGRAM
# ================================

def save(msg):
    if "video" not in msg:
        return

    title = "Film"
    if msg.get("caption"):
        title = msg["caption"].split("\n")[0]

    poster = "https://via.placeholder.com/300x450?text=Movie"

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        msg.get("caption",""),
        msg["video"]["file_id"],
        poster
    ))

    con.commit()
    con.close()

# ================================
# API
# ================================

@app.route("/api")
def api():
    con = db()
    cur = con.cursor()

    rows = cur.execute("SELECT * FROM movies").fetchall()
    con.close()

    return jsonify([
        {
            "id": r[0],
            "title": r[1],
            "story": r[2],
            "file_id": r[3],
            "poster": r[4]
        } for r in rows
    ])

# ================================
# PLAY
# ================================

@app.route("/play/<id>")
def play(id):
    uid = request.args.get("uid")

    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()

    if m and uid:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m[3],
            "caption": m[1]
        })

    con.close()
    return "OK"

# ================================
# UI (SAUBER + FUNKTIONIERT)
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {background:#111;color:white;font-family:sans-serif;margin:0}

.hero {
    height:50vh;
    display:flex;
    align-items:end;
    padding:20px;
    background:#222;
}

.row {
    display:flex;
    overflow-x:auto;
    padding:20px;
}

.card {
    margin-right:10px;
    cursor:pointer;
}

.card img {
    width:140px;
    border-radius:10px;
}

.modal {
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:black;
    display:none;
    padding:20px;
}
</style>

<body>

<div class="hero">🎬 Netflix Clone</div>

<div class="row" id="row"></div>

<div id="modal" class="modal">
    <h1 id="title"></h1>
    <p id="story"></p>
    <button onclick="play()">▶️ Play</button>
    <button onclick="closeModal()">❌</button>
</div>

<script>
let DATA = [];
let current = null;
let uid = prompt("Deine Telegram ID:");

fetch("/api")
.then(r=>r.json())
.then(data=>{
    DATA = data;

    let row = document.getElementById("row");

    data.forEach(m=>{
        let div = document.createElement("div");
        div.className = "card";

        div.innerHTML = `<img src="${m.poster}">`;

        div.onclick = ()=>{
            current = m;
            document.getElementById("modal").style.display="block";
            document.getElementById("title").innerText = m.title;
            document.getElementById("story").innerText = m.story;
        };

        row.appendChild(div);
    });
});

function closeModal(){
    document.getElementById("modal").style.display="none";
}

function play(){
    window.location="/play/"+current.id+"?uid="+uid;
}
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