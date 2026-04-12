# ================================
# 🎬 ULTIMATE NETFLIX UI SYSTEM
# ================================

import os
import sqlite3
import requests
import time
from flask import Flask, request, jsonify, render_template_string, Response

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
        views INTEGER,
        progress INTEGER DEFAULT 0
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# SAVE
# ================================

def save(msg):
    if "video" not in msg:
        return

    title = msg.get("caption","Film").split("\n")[0]

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        msg.get("caption",""),
        msg["video"]["file_id"],
        0,
        0
    ))

    con.commit()
    con.close()

# ================================
# TELEGRAM FILE
# ================================

def get_file_url(file_id):
    r = requests.get(f"{URL}/getFile?file_id={file_id}").json()
    file_path = r["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

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

    file_url = get_file_url(m[3])

    def generate():
        with requests.get(file_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*1024):
                yield chunk

    return Response(generate(), content_type="video/mp4")

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
        "views": r[4],
        "progress": r[5]
    } for r in rows]

    data.sort(key=lambda x: x["views"], reverse=True)

    return jsonify(data)

# ================================
# SAVE PROGRESS
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
# UI
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {margin:0;background:#141414;color:white;font-family:sans-serif}

/* HERO */
.hero {
    height:60vh;
    display:flex;
    align-items:end;
    padding:30px;
    background:#222;
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
    background:#222;
    padding:15px;
    cursor:pointer;
    position:relative;
}

/* PROGRESS BAR */
.progress {
    height:4px;
    background:red;
    position:absolute;
    bottom:0;
    left:0;
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
    z-index:10;
}

video {width:100%}
</style>

<body>

<div id="hero" class="hero"></div>

<h2 style="padding-left:20px">🔥 Trending</h2>
<div id="row" class="row"></div>

<div id="modal" class="modal">
    <h1 id="title"></h1>
    <p id="story"></p>
    <video id="video" controls></video>
    <button onclick="closeModal()">❌</button>
</div>

<script>
let DATA = [];
let current = null;

fetch("/api")
.then(r=>r.json())
.then(data=>{
    DATA = data;

    if(data.length){
        document.getElementById("hero").innerText = data[0].title;
    }

    let row = document.getElementById("row");

    data.forEach(m=>{
        let card = document.createElement("div");
        card.className = "card";
        card.innerText = m.title;

        // Progress bar
        let p = document.createElement("div");
        p.className = "progress";
        p.style.width = m.progress + "%";
        card.appendChild(p);

        card.onclick = ()=>{
            current = m;

            document.getElementById("modal").style.display="block";
            document.getElementById("title").innerText = m.title;
            document.getElementById("story").innerText = m.story;

            let video = document.getElementById("video");
            video.src = "/stream/" + m.id;

            video.ontimeupdate = ()=>{
                let percent = (video.currentTime / video.duration) * 100;

                fetch("/progress", {
                    method:"POST",
                    headers:{"Content-Type":"application/json"},
                    body:JSON.stringify({
                        id: m.id,
                        progress: percent
                    })
                });
            };
        };

        row.appendChild(card);
    });
});

function closeModal(){
    document.getElementById("modal").style.display="none";
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