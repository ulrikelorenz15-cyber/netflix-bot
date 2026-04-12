# ================================
# 🎬 REAL NETFLIX STREAM SYSTEM
# ================================

import os
import sqlite3
import requests
import re
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
        file_id TEXT
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

    title = "Film"
    if msg.get("caption"):
        title = msg["caption"].split("\n")[0]

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        msg.get("caption",""),
        msg["video"]["file_id"]
    ))

    con.commit()
    con.close()

# ================================
# GET FILE URL
# ================================

def get_file_url(file_id):
    r = requests.get(f"{URL}/getFile?file_id={file_id}").json()
    file_path = r["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

# ================================
# STREAM ROUTE
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
                if chunk:
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

    return jsonify([
        {
            "id": r[0],
            "title": r[1],
            "story": r[2]
        } for r in rows
    ])

# ================================
# UI (ECHTER PLAYER)
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {background:black;color:white;font-family:sans-serif;margin:0}

.grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:10px;
    padding:10px;
}

.card {
    background:#222;
    padding:20px;
    cursor:pointer;
}

video {
    width:100%;
}
</style>

<body>

<h2 style="padding:10px">🎬 Meine Filme</h2>

<div id="grid" class="grid"></div>

<div id="player"></div>

<script>
fetch("/api")
.then(r=>r.json())
.then(data=>{
    let grid = document.getElementById("grid");

    data.forEach(m=>{
        let div = document.createElement("div");
        div.className = "card";
        div.innerText = m.title;

        div.onclick = ()=>{
            document.getElementById("player").innerHTML = `
                <video controls autoplay>
                    <source src="/stream/${m.id}" type="video/mp4">
                </video>
            `;
        };

        grid.appendChild(div);
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