# ================================
# 🎬 ULTIMATE FINAL SYSTEM (ALL-IN)
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, jsonify, Response, render_template_string

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
TMDB_KEY = os.getenv("TMDB_KEY")
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
        cover TEXT,
        progress INTEGER
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# 🎬 TMDB COVER
# ================================

def get_cover(title):
    try:
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

    return "https://placehold.co/300x450/111/fff?text=" + title.replace(" ","+")

# ================================
# PARSER
# ================================

def extract_data(caption):
    if not caption:
        return "Film", "-"

    title_match = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title_match.group(1) if title_match else caption.split("\\n")[0]

    story_match = re.search(r"STORY\\s*(.*)", caption, re.S)
    story = story_match.group(1).strip()[:300] if story_match else "-"

    return title.strip(), story.strip()

# ================================
# SAVE
# ================================

def save(msg):
    if "video" not in msg:
        return

    title, story = extract_data(msg.get("caption",""))
    cover = get_cover(title)

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        story,
        msg["video"]["file_id"],
        cover,
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

    file_url = get_file_url(m[3])

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
            "cover": r[4],
            "progress": r[5]
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
# UI FINAL
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {margin:0;background:#141414;color:white;font-family:sans-serif}

/* SEARCH */
.search {
    padding:15px;
    width:100%;
    background:#111;
    border:none;
    color:white;
    font-size:16px;
}

/* HERO */
.hero {
    height:60vh;
    display:flex;
    align-items:end;
    padding:30px;
    background-size:cover;
    font-size:40px;
}

/* ROW */
.row {
    display:flex;
    overflow-x:auto;
    padding:20px;
}

/* CARD */
.card {
    min-width:150px;
    height:220px;
    margin-right:10px;
    background-size:cover;
    border-radius:10px;
    position:relative;
    cursor:pointer;
    transition:0.3s;
}

.card:hover {
    transform:scale(1.2);
}

/* OVERLAY */
.card-title {
    position:absolute;
    bottom:0;
    background:linear-gradient(to top, black, transparent);
    width:100%;
    padding:10px;
    font-size:12px;
}

/* MODAL */
.modal {
    position:fixed;
    width:100%;
    height:100%;
    background:black;
    display:none;
    top:0;
    left:0;
    padding:20px;
}

video {width:100%}
</style>

<body>

<input class="search" placeholder="🔍 Suche..." oninput="search(this.value)">

<div id="hero" class="hero"></div>

<div id="row" class="row"></div>

<div id="modal" class="modal">
    <h1 id="title"></h1>
    <p id="story"></p>
    <video id="video" controls autoplay></video>
    <button onclick="closeModal()">❌</button>
</div>

<script>
let DATA = [];

fetch("/movies")
.then(r=>r.json())
.then(data=>{
    DATA = data;
    render(data);
});

function render(data){
    let row = document.getElementById("row");
    row.innerHTML="";

    if(data.length){
        document.getElementById("hero").style.backgroundImage =
            "url("+data[0].cover+")";
        document.getElementById("hero").innerText = data[0].title;
    }

    data.forEach(m=>{
        let card = document.createElement("div");
        card.className="card";
        card.style.backgroundImage = "url("+m.cover+")";

        card.innerHTML = `<div class="card-title">${m.title}</div>`;

        card.onclick = ()=>{
            document.getElementById("modal").style.display="block";
            document.getElementById("title").innerText=m.title;
            document.getElementById("story").innerText=m.story;

            document.getElementById("video").src="/stream/"+m.id;
        };

        row.appendChild(card);
    });
}

function search(q){
    let filtered = DATA.filter(m =>
        m.title.toLowerCase().includes(q.toLowerCase())
    );
    render(filtered);
}

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
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)