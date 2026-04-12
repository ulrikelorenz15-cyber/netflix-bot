# ================================
# 🎬 ULTIMATE PLATFORM MODE
# ================================

import os
import sqlite3
import requests
import re
import time
from flask import Flask, request, jsonify, Response, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
        category TEXT,
        progress INTEGER
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# COVER
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
# PARSER
# ================================

def extract_data(caption):
    if not caption:
        return "Film", "-", "General"

    title_match = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title_match.group(1) if title_match else caption.split("\n")[0]

    story_match = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption, re.S)
    story = story_match.group(1).strip() if story_match else "-"

    tags = re.findall(r"#([A-Za-z]+)", caption)
    category = tags[0] if tags else "General"

    return title.strip(), story.strip(), category

# ================================
# SAVE TELEGRAM
# ================================

def save(msg):
    if "video" not in msg:
        return

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
    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (id,)).fetchone()
    con.close()

    url = get_file(m[3])

    def generate():
        with requests.get(url, stream=True) as r:
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
            "category": r[5],
            "progress": r[6]
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
# 🎬 UI (ULTIMATE PLATFORM)
# ================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width">

<style>
body {margin:0;background:#141414;color:white;font-family:sans-serif}

/* NAV */
.nav {
  display:flex;
  justify-content:space-between;
  padding:15px;
  background:black;
}

.nav input {
  background:#222;
  border:none;
  color:white;
}

/* HERO */
.hero {
  height:60vh;
  display:flex;
  align-items:end;
  padding:30px;
  background-size:cover;
}

/* ROW */
.row {
  display:flex;
  overflow-x:auto;
  padding:20px;
}

/* CARD */
.card {
  width:180px;
  height:260px;
  margin-right:10px;
  position:relative;
  border-radius:10px;
  overflow:hidden;
  cursor:pointer;
}

.preview {
  position:absolute;
  width:100%;
  height:100%;
  object-fit:cover;
  opacity:0;
}

.card:hover .preview {
  opacity:1;
}

.cover {
  position:absolute;
  width:100%;
  height:100%;
  background-size:cover;
}

.title {
  position:absolute;
  bottom:0;
  padding:10px;
  background:linear-gradient(to top, black, transparent);
}

/* MODAL */
.modal {
  position:fixed;
  top:0;
  width:100%;
  height:100%;
  background:black;
  display:none;
}
</style>

<body>

<div class="nav">
  <div>🎬 NETFLIX</div>
  <input placeholder="Suche..." oninput="search(this.value)">
</div>

<div id="hero" class="hero"></div>
<div id="content"></div>

<div id="modal" class="modal">
  <video id="video" controls autoplay></video>
  <button onclick="closeModal()">✖</button>
</div>

<script>
let DATA=[];
let WATCHLIST = JSON.parse(localStorage.getItem("watchlist")||"[]");

fetch("/movies")
.then(r=>r.json())
.then(data=>{
  DATA=data;
  render(data);
});

function render(data){
  let content=document.getElementById("content");
  content.innerHTML="";

  if(data.length){
    document.getElementById("hero").style.backgroundImage =
      "url("+data[0].cover+")";
  }

  let categories=[...new Set(data.map(m=>m.category))];

  categories.forEach(cat=>{
    let title=document.createElement("h2");
    title.innerText=cat;
    content.appendChild(title);

    let row=document.createElement("div");
    row.className="row";

    data.filter(m=>m.category===cat).forEach(m=>{
      let card=document.createElement("div");
      card.className="card";

      card.innerHTML=`
        <video class="preview" src="/stream/${m.id}" muted loop></video>
        <div class="cover" style="background-image:url(${m.cover})"></div>
        <div class="title">${m.title}</div>
      `;

      card.onclick=()=>{
        let v=document.getElementById("video");
        v.src="/stream/"+m.id;
        document.getElementById("modal").style.display="block";
      };

      row.appendChild(card);
    });

    content.appendChild(row);
  });
}

function search(q){
  let f=DATA.filter(m=>m.title.toLowerCase().includes(q.toLowerCase()));
  render(f);
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))