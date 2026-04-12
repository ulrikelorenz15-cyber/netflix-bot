# ================================
# 🎬 NETFLIX NEXT LEVEL FINAL
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
        category TEXT,
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

def extract(msg):
    text = msg.get("caption","")

    title = "Film"
    if text:
        title = text.split("\n")[0]

    # Kategorie aus Hashtag
    tags = re.findall(r"#(\w+)", text)
    category = tags[0] if tags else "Trending"

    story = text if text else "-"

    return title, category, story

# ================================
# SAVE
# ================================

def save(msg):
    if "video" not in msg:
        return

    title, category, story = extract(msg)

    poster = "https://via.placeholder.com/300x450?text=" + title.replace(" ", "+")

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        story,
        category,
        msg["video"]["file_id"],
        poster,
        0,
        time.time()
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

    data = [{
        "id": r[0],
        "title": r[1],
        "story": r[2],
        "category": r[3],
        "file_id": r[4],
        "poster": r[5],
        "views": r[6],
        "timestamp": r[7]
    } for r in rows]

    # 🔥 Trending Sortierung
    data.sort(key=lambda x: x["views"], reverse=True)

    return jsonify(data)

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
        cur.execute("UPDATE movies SET views=views+1 WHERE id=?", (id,))
        con.commit()

        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m[4],
            "caption": m[1]
        })

    con.close()
    return "OK"

# ================================
# UI
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {background:#141414;color:white;margin:0;font-family:sans-serif}

/* NAV */
.nav {
    position:fixed;
    width:100%;
    padding:15px;
    background:linear-gradient(to bottom, rgba(0,0,0,0.9), transparent);
    z-index:10;
}

/* HERO */
.hero {
    height:60vh;
    display:flex;
    align-items:end;
    padding:30px;
    background-size:cover;
    font-size:30px;
}

/* ROW */
.row {
    display:flex;
    overflow-x:auto;
    padding:20px;
}

/* CARD */
.card {
    margin-right:10px;
    position:relative;
    transition:0.3s;
    cursor:pointer;
}

.card img {
    width:150px;
    border-radius:10px;
}

.card:hover {
    transform:scale(1.1);
}

/* OVERLAY */
.overlay {
    position:absolute;
    bottom:0;
    width:100%;
    background:rgba(0,0,0,0.8);
    opacity:0;
    padding:5px;
    font-size:12px;
}

.card:hover .overlay {
    opacity:1;
}

/* MODAL */
.modal {
    position:fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    background:black;
    display:none;
    padding:20px;
    z-index:20;
}
</style>

<body>

<div class="nav">🎬 NETFLIX</div>

<div id="hero" class="hero"></div>

<div id="content"></div>

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

    if(data.length){
        document.getElementById("hero").style.backgroundImage =
            "url("+data[0].poster+")";
        document.getElementById("hero").innerText = data[0].title;
    }

    // 🔥 Kategorien dynamisch
    let grouped = {};

    data.forEach(m=>{
        if(!grouped[m.category]) grouped[m.category]=[];
        grouped[m.category].push(m);
    });

    let container = document.getElementById("content");

    for(let cat in grouped){
        let title = document.createElement("h2");
        title.innerText = cat;

        let row = document.createElement("div");
        row.className = "row";

        grouped[cat].forEach(m=>{
            let card = document.createElement("div");
            card.className = "card";

            card.innerHTML = `
                <img src="${m.poster}">
                <div class="overlay">${m.title}</div>
            `;

            card.onclick = ()=>{
                current = m;
                document.getElementById("modal").style.display = "block";
                document.getElementById("title").innerText = m.title;
                document.getElementById("story").innerText = m.story;
            };

            row.appendChild(card);
        });

        container.appendChild(title);
        container.appendChild(row);
    }
});

function closeModal(){
    document.getElementById("modal").style.display = "none";
}

function play(){
    window.location = "/play/" + current.id + "?uid=" + uid;
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