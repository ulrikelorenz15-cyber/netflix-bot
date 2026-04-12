# ================================
# 🎬 ULTIMATE NETFLIX SYSTEM
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "netflix_secret"

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
TMDB_KEY = os.getenv("TMDB_KEY")

DATA_FILE = "data.json"
USER_FILE = "users.json"

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def load_users():
    if os.path.exists(USER_FILE):
        return json.load(open(USER_FILE))
    return {}

def save_users(data):
    json.dump(data, open(USER_FILE, "w"))

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

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

    story = "-"
    s = re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S)
    if s:
        story = s.group(1)

    return {
        "title": t.group(1),
        "year": t.group(2),
        "story": story
    }

# ================================
# USER SYSTEM
# ================================

def get_current_user():
    return session.get("uid")

def update_progress(uid, movie_id):
    users = load_users()
    user = users.get(uid, {"history": []})

    if movie_id in user["history"]:
        user["history"].remove(movie_id)

    user["history"].insert(0, movie_id)
    user["history"] = user["history"][:10]

    users[uid] = user
    save_users(users)

# ================================
# LOGIN
# ================================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        uid = request.form["uid"]
        session["uid"] = uid
        return redirect("/")
    return """
    <form method="post">
        Telegram ID:<input name="uid">
        <button>Login</button>
    </form>
    """

# ================================
# HOME UI
# ================================

@app.route("/")
def home():
    uid = get_current_user()
    if not uid:
        return redirect("/login")

    data = load_data()
    users = load_users()

    movies = data["movies"]
    history_ids = users.get(uid, {}).get("history", [])

    continue_movies = [m for m in movies if m["id"] in history_ids]

    hero = movies[0] if movies else None

    return render_template_string("""
    <html>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    body {background:#141414;color:white;margin:0;font-family:sans-serif}
    .nav {position:fixed;width:100%;background:#000;padding:10px}
    .row {display:flex;overflow-x:auto;padding:10px}
    .card {margin-right:10px;position:relative}
    .card img {width:140px;border-radius:8px}

    .progress {
        position:absolute;
        bottom:0;
        height:5px;
        background:red;
        width:50%;
    }

    .hero {height:60vh;background-size:cover;display:flex;align-items:flex-end;padding:20px}
    </style>

    <div class="nav">👤 {{uid}}</div>

    {% if hero %}
    <div class="hero" style="background-image:url('{{hero.poster}}')">
        {{hero.title}}
    </div>
    {% endif %}

    <h3>▶️ Continue Watching</h3>
    <div class="row">
    {% for m in continue_movies %}
        <div class="card">
            <img src="{{m.poster}}">
            <div class="progress"></div>
        </div>
    {% endfor %}
    </div>

    <h3>🔥 Trending</h3>
    <div class="row">
    {% for m in movies %}
        <div class="card">
            <a href="/play/{{m.id}}">
                <img src="{{m.poster}}">
            </a>
        </div>
    {% endfor %}
    </div>

    """, movies=movies, hero=hero, continue_movies=continue_movies, uid=uid)

# ================================
# PLAY
# ================================

@app.route("/play/<mid>")
def play(mid):
    uid = get_current_user()
    data = load_data()

    m = next(x for x in data["movies"] if x["id"] == mid)

    if uid:
        update_progress(uid, mid)

        requests.post(f"{URL}/sendVideo", json={
            "chat_id": uid,
            "video": m["file_id"],
            "caption": f"▶️ {m['title']}"
        })

    return redirect("/")

# ================================
# ADMIN
# ================================

@app.route("/admin")
def admin():
    data = load_data()
    return render_template_string("""
    <h1>Admin</h1>
    {% for m in data.movies %}
        <div>
            {{m.title}}
            <a href="/edit/{{m.id}}">Edit</a>
            <a href="/delete/{{m.id}}">Delete</a>
        </div>
    {% endfor %}
    """, data=data)

@app.route("/edit/<mid>", methods=["GET","POST"])
def edit(mid):
    data = load_data()
    m = next(x for x in data["movies"] if x["id"] == mid)

    if request.method == "POST":
        m["title"] = request.form["title"]
        m["poster"] = request.form["poster"]
        m["story"] = request.form["story"]
        save_data(data)
        return redirect("/admin")

    return render_template_string("""
    <form method="post">
        Title:<input name="title" value="{{m.title}}">
        Poster:<input name="poster" value="{{m.poster}}">
        <textarea name="story">{{m.story}}</textarea>
        <button>Save</button>
    </form>
    """, m=m)

@app.route("/delete/<mid>")
def delete(mid):
    data = load_data()
    data["movies"] = [m for m in data["movies"] if m["id"] != mid]
    save_data(data)
    return redirect("/admin")

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

            if info:
                data["movies"].append({
                    "id": get_id(data),
                    **info,
                    "file_id": msg["video"]["file_id"],
                    "poster": get_poster(info["title"])
                })
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