# ================================
# 🎬 NETFLIX SYSTEM (RENDER READY)
# ================================

import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify, render_template_string

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

DATA_FILE = "data.json"

app = Flask(__name__)

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# POSTER
# ================================

def get_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

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
        "rating": re.search(r"⭐\s*([0-9.]+)", text).group(1),
        "runtime": re.search(r"⏱\s*([0-9]+\s*Min)", text).group(1),
        "genre": re.findall(r"#(\w+)", text)[:2],
        "story": re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S).group(1).strip()
    }

# ================================
# TRENDING
# ================================

def score(m):
    return m["views"] * 2 + (5 - (time.time() - m["timestamp"]) / 86400)

# ================================
# WEB APP
# ================================

@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
    <style>
    body{background:#141414;color:white;font-family:sans-serif}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,180px);gap:15px}
    .card img{width:180px;border-radius:10px}
    .card:hover{transform:scale(1.2)}
    </style>
    </head>
    <body>

    <h1>🎬 Netflix Clone</h1>
    <div id="grid" class="grid"></div>

    <script>
    fetch('/api/movies')
    .then(r=>r.json())
    .then(data=>{
        let grid=document.getElementById("grid");
        data.forEach(m=>{
            let div=document.createElement("div");
            div.className="card";
            div.innerHTML=`<img src="${m.poster}">`;
            grid.appendChild(div);
        });
    });
    </script>

    </body>
    </html>
    """)

@app.route("/api/movies")
def api_movies():
    return jsonify(load_data()["movies"])

# ================================
# TELEGRAM WEBHOOK
# ================================

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    data = load_data()

    print("UPDATE:", update)

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg:
            info = extract(msg.get("caption", ""))

            if not info:
                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Fehler beim Erkennen"
                })
                return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg["video"]["file_id"],
                "views": 0,
                "timestamp": time.time(),
                "poster": get_poster(info["title"])
            }

            data["movies"].append(entry)
            save_data(data)

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ {info['title']} gespeichert"
            })

    return "ok"

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 RENDER READY SYSTEM START")

    # SET WEBHOOK
    if os.getenv("WEBHOOK_URL"):
        requests.get(f"{URL}/setWebhook?url={os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)