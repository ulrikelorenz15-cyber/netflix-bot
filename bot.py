import os, json, re, time, requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies":[]}

def save_data(data):
    json.dump(data, open(DATA_FILE,"w"))

def get_id(data):
    return str(len(data["movies"])+1).zfill(4)

def send(msg):
    requests.post(f"{URL}/sendMessage", json=msg)

# ================================
# 🎬 PARSER (DEIN FORMAT)
# ================================

def parse(text):
    t = re.search(r"🎬\s*(.*?)\s*\((\d{4})\)", text)
    if not t: return None

    return {
        "title": t.group(1),
        "year": t.group(2),
        "rating": re.search(r"⭐\s*([0-9.]+)", text).group(1),
        "runtime": re.search(r"⏱\s*([0-9]+\s*Min)", text).group(1),
        "genre": re.findall(r"#(\w+)", text)[:2],
        "story": re.search(r"📖 STORY\s*(.*?)\s*━━━━━━━━", text, re.S).group(1).strip()
    }

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def hook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat = msg["chat"]["id"]

        if "video" in msg:
            data = load_data()
            info = parse(msg.get("caption",""))

            if not info:
                send({"chat_id":chat,"text":"❌ Fehler"})
                return "ok"

            entry = {
                "id": get_id(data),
                **info,
                "file_id": msg["video"]["file_id"],
                "views":0,
                "timestamp":time.time(),
                "poster": f"https://image.pollinations.ai/prompt/{info['title']}"
            }

            data["movies"].append(entry)
            save_data(data)

            send({
                "chat_id":chat,
                "text":f"✅ {info['title']} gespeichert"
            })

    return "ok"

if __name__ == "__main__":
    requests.get(f"{URL}/setWebhook?url=YOUR_URL/webhook/{TOKEN}")
    app.run(port=5001)