# ================================
# 🎬 NETFLIX ULTRA UI SYSTEM
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, render_template_string

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"
TMDB_KEY = os.getenv("TMDB_KEY")

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": [], "series": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(arr):
    return str(len(arr)+1).zfill(4)

# ================================
# AUTO COVER
# ================================

def get_poster(title):
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": TMDB_KEY, "query": title}
        ).json()

        if r["results"]:
            return "https://image.tmdb.org/t/p/w500" + r["results"][0]["poster_path"]
    except:
        pass

    return "https://dummyimage.com/300x450/000/fff&text=No+Cover"

# ================================
# PARSER
# ================================

def extract(text):
    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t:
        return None

    return {
        "title": t.group(1),
        "year": t.group(2),
        "story": re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S).group(1) if "STORY" in text else "-"
    }

# ================================
# 🎬 HOME (ULTRA UI)
# ================================

@app.route("/")
def home():
    data = load_data()

    movies = data["movies"]
    hero = movies[0] if movies else None

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    body {
        background:#141414;
        color:white;
        font-family:sans-serif;
        margin:0;
    }

    /* NAV */
    .nav {
        position:fixed;
        top:0;
        width:100%;
        background:rgba(0,0,0,0.8);
        padding:10px;
        z-index:10;
    }

    .nav a {
        margin-right:15px;
        color:white;
        text-decoration:none;
        font-weight:bold;
    }

    /* HERO */
    .hero {
        height:70vh;
        background-size:cover;
        display:flex;
        align-items:flex-end;
        padding:20px;
        font-size:30px;
        font-weight:bold;
    }

    /* ROW */
    .row {
        display:flex;
        overflow-x:auto;
        padding:10px;
    }

    /* CARD */
    .card {
        position:relative;
        margin-right:10px;
        transition:0.3s;
    }

    .card img {
        width:140px;
        border-radius:8px;
    }

    .card:hover {
        transform:scale(1.2);
    }

    .overlay {
        position:absolute;
        bottom:0;
        width:100%;
        background:rgba(0,0,0,0.7);
        font-size:12px;
        padding:5px;
    }

    /* GRID */
    .grid {
        display:grid;
        grid-template-columns:repeat(auto-fill, minmax(120px,1fr));
        gap:10px;
        padding:10px;
    }

    /* MODAL */
    .modal {
        display:none;
        position:fixed;
        top:0;
        left:0;
        width:100%;
        height:100%;
        background:black;
        z-index:20;
        padding:20px;
    }

    </style>
    </head>

    <body>

    <!-- NAV -->
    <div class="nav">
        <a href="#">🏠 Home</a>
        <a href="#movies">🎬 Filme</a>
    </div>

    <!-- HERO -->
    {% if hero %}
    <div class="hero" style="background-image:url('{{hero.poster}}')">
        {{hero.title}}
    </div>
    {% endif %}

    <!-- TRENDING -->
    <h2 style="padding:10px;">🔥 Trending</h2>
    <div class="row">
    {% for m in movies[:10] %}
        <div class="card" onclick="openModal('{{m.title}}','{{m.story}}','{{m.poster}}','{{m.id}}')">
            <img src="{{m.poster}}">
            <div class="overlay">{{m.title}}</div>
        </div>
    {% endfor %}
    </div>

    <!-- GRID -->
    <h2 id="movies" style="padding:10px;">🎬 Alle Filme</h2>
    <div class="grid">
    {% for m in movies %}
        <div class="card" onclick="openModal('{{m.title}}','{{m.story}}','{{m.poster}}','{{m.id}}')">
            <img src="{{m.poster}}">
            <div class="overlay">{{m.title}}</div>
        </div>
    {% endfor %}
    </div>

    <!-- MODAL -->
    <div id="modal" class="modal">
        <h1 id="m_title"></h1>
        <img id="m_img" style="width:200px;">
        <p id="m_story"></p>

        <button onclick="play()">▶️ Play</button>
        <button onclick="closeModal()">❌ Close</button>
    </div>

    <script>
    let currentId = null;

    function openModal(title, story, poster, id){
        document.getElementById("modal").style.display="block";
        document.getElementById("m_title").innerText=title;
        document.getElementById("m_story").innerText=story;
        document.getElementById("m_img").src=poster;
        currentId = id;
    }

    function closeModal(){
        document.getElementById("modal").style.display="none";
    }

    function play(){
        let uid = prompt("Deine Telegram ID:");
        window.location = "/play/"+currentId+"?uid="+uid;
    }
    </script>

    </body>
    </html>
    """, movies=movies, hero=hero)

# ================================
# PLAY
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = request.args.get("uid")
    data = load_data()

    m = next(x for x in data["movies"] if x["id"] == mid)

    if uid:
        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m["file_id"],
            "caption": f"▶️ {m['title']}"
        })

    return "▶️ Wird abgespielt..."

# ================================
# WEBHOOK
# ================================

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]

        if "video" in msg:
            data = load_data()
            info = extract(msg.get("caption",""))

            if not info:
                return "ok"

            entry = {
                "id": get_id(data["movies"]),
                **info,
                "file_id": msg["video"]["file_id"],
                "poster": get_poster(info["title"])
            }

            data["movies"].append(entry)
            save_data(data)

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    if TOKEN and os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)