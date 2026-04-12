# ================================
# 🎬 NETFLIX BOT + WEB APP (FINAL)
# ================================

import os
import json
import requests
import re
import time
import threading
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None
DATA_FILE = "data.json"

# ================================
# SAFE START
# ================================

if not TOKEN:
    print("❌ BOT_TOKEN fehlt!")
else:
    print("✅ BOT TOKEN OK")

# ================================
# DATA
# ================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print("LOAD ERROR:", e)
    return {"movies": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("SAVE ERROR:", e)

def get_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# SAFE REGEX
# ================================

def safe(pattern, text):
    try:
        m = re.search(pattern, text, re.S)
        return m.group(1).strip() if m else "-"
    except:
        return "-"

# ================================
# PARSER (DEIN FORMAT)
# ================================

def extract(text):
    try:
        t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
        if not t:
            return None

        return {
            "title": t.group(1).strip(),
            "year": t.group(2),
            "rating": safe(r"⭐\s*([0-9.]+)", text),
            "runtime": safe(r"⏱\s*([0-9]+\s*Min)", text),
            "genre": re.findall(r"#(\w+)", text)[:2] or ["Unknown"],
            "story": safe(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text)
        }
    except Exception as e:
        print("PARSE ERROR:", e)
        return None

# ================================
# POSTER
# ================================

def get_poster(title):
    return f"https://image.pollinations.ai/prompt/{title}+movie+poster"

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
    .grid{display:grid;grid-template-columns:repeat(auto-fill,180px);gap:15px;padding:20px}
    .card img{width:180px;border-radius:10px}
    .card:hover{transform:scale(1.2)}
    </style>
    </head>
    <body>

    <h1>🎬 Netflix System</h1>
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
    try:
        update = request.get_json()
        print("UPDATE:", update)

        if not update or "message" not in update:
            return "ok"

        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "video" in msg or "document" in msg:
            data = load_data()
            caption = msg.get("caption", "")

            info = extract(caption)

            if not info:
                requests.post(f"{URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "❌ Film nicht erkannt"
                })
                return "ok"

            # DUPLICATE CHECK
            for m in data["movies"]:
                if m["title"].lower() == info["title"].lower():
                    requests.post(f"{URL}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": f"⚠️ Existiert bereits: {info['title']}"
                    })
                    return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg.get("video", msg.get("document"))["file_id"],
                "views": 0,
                "timestamp": time.time(),
                "poster": get_poster(info["title"])
            }

            data["movies"].append(entry)
            save_data(data)

            requests.post(f"{URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"✅ Gespeichert: {info['title']}"
            })

        return "ok"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "ok"

# ================================
# 🔄 KEEP ALIVE (ANTI SLEEP)
# ================================

def keep_alive():
    while True:
        try:
            url = os.getenv("WEBHOOK_URL")
            if url:
                requests.get(url)
                print("🔄 KEEP ALIVE")
        except Exception as e:
            print("PING ERROR:", e)

        time.sleep(300)

threading.Thread(target=keep_alive, daemon=True).start()

# ================================
# START
# ================================

if __name__ == "__main__":
    print("🔥 FINAL SYSTEM START")

    if TOKEN and os.getenv("WEBHOOK_URL"):
        try:
            webhook_url = f"{os.getenv('WEBHOOK_URL')}/webhook/{TOKEN}"
            print("SET WEBHOOK:", webhook_url)
            requests.get(f"{URL}/setWebhook?url={webhook_url}")
        except Exception as e:
            print("WEBHOOK ERROR:", e)

    port = int(os.environ.get("PORT", 10000))
    print("PORT:", port)

    app.run(host="0.0.0.0", port=port, debug=False)