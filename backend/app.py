# ================================
# 🎬 FINAL NETFLIX SYSTEM (STABLE)
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

    return "https://placehold.co/300x450?text=" + title

# ================================
# PARSER
# ================================

def extract_data(caption):
    if not caption:
        return "Film", "-", "General"

    title = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title.group(1) if title else caption.split("\n")[0]

    story = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption, re.S)
    story = story.group(1).strip() if story else "-"

    tags = re.findall(r"#([A-Za-z]+)", caption)
    category = tags[0] if tags else "General"

    return title, story, category

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

    if not m:
        return "Not found"

    url = get_file(m[3])

    def generate():
        with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(1024*1024):
                if chunk:
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
# 🎬 UI (FINAL)
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
  padding:15px;
  background:black;
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
  width:160px;
  height:240px;
  margin-right:10px;
  background-size:cover;
  border-radius:10px;
  cursor:pointer;
  transition:0.3s;
}

.card:hover {
  transform:scale(1.2);
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

video {
  width:100%;
}
</style>

<body>

<div class="nav">🎬 NETFLIX</div>

<div id="hero" class="hero"></div>

<div id="row" class="row"></div>

<div id="modal" class="modal">
  <video id="video" controls autoplay></video>
  <button onclick="closeModal()">✖</button>
</div>

<script>
fetch("/movies")
.then(r=>r.json())
.then(data=>{

  if(data.length){
    document.getElementById("hero").style.backgroundImage =
      "url("+data[0].cover+")";
  }

  let row=document.getElementById("row");

  data.forEach(m=>{
    let card=document.createElement("div");
    card.className="card";
    card.style.backgroundImage="url("+m.cover+")";

    card.onclick=()=>{
      document.getElementById("modal").style.display="block";
      document.getElementById("video").src="/stream/"+m.id;

      let v=document.getElementById("video");

      v.ontimeupdate=()=>{
        let p=(v.currentTime/v.duration)*100;

        fetch("/progress",{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            id:m.id,
            progress:p
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))