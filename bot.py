# ================================
# 🎬 NETFLIX BOT FINAL STABLE
# ================================

import os
import json
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
OMDB_KEY = "a3776f86"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
USER_STYLE = {}

# ================================
# DATA
# ================================

def load_data():
    default = {"movies": [], "categories": {}}

    if os.path.exists(DATA_FILE):
        try:
            data = json.load(open(DATA_FILE))
            for k in default:
                if k not in data:
                    data[k] = default[k]
            return data
        except:
            return default

    return default

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

# ================================
# OMDb
# ================================

def get_movie(title):
    try:
        r = requests.get(f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}&plot=full").json()
        if r.get("Response") == "False":
            return None
        return r
    except:
        return None

# ================================
# KI STORY (FINAL FIX)
# ================================

def generate_story(title, plot, genre, user_id):
    try:
        if not plot or plot == "N/A":
            plot = f"{title} ist ein Film aus dem Genre {genre}."

        prompt = f"""
Schreibe eine deutsche Filmbeschreibung.

Film: {title}
Genre: {genre}

Inhalt:
{plot}

1 Satz Kurzbeschreibung + 4 Sätze Story.

Nur Deutsch.
Format:
KURZ: ...
LANG: ...
"""

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        text = res.choices[0].message.content.strip()

        if "KURZ:" in text and "LANG:" in text:
            short = text.split("KURZ:")[1].split("LANG:")[0].strip()
            long = text.split("LANG:")[1].strip()
        else:
            raise Exception("Format Fehler")

        if len(long) < 40:
            raise Exception("Zu kurz")

        return short, long

    except Exception as e:
        print("KI FAIL:", e)

        # 🔥 IMMER funktionierender Fallback
        return (
            "Ein intensiver Film voller Konflikte.",
            f"{title} erzählt die Geschichte eines Protagonisten, der in eine gefährliche Situation gerät und sich gegen mächtige Gegner behaupten muss. Während sich die Ereignisse zuspitzen, wird klar, dass hinter allem größere Zusammenhänge stecken. Jede Entscheidung bringt neue Risiken mit sich und zwingt ihn, an seine Grenzen zu gehen. Am Ende steht mehr auf dem Spiel als nur sein eigenes Schicksal."
        )

# ================================
# BANNER
# ================================

def create_banner(title):
    img = Image.new("RGB", (1280, 720), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0,0), title.upper(), font=font)
    x = (1280 - (bbox[2]-bbox[0]))//2
    y = (720 - (bbox[3]-bbox[1]))//2

    draw.text((x,y), title.upper(), fill="white", font=font)

    path = f"/tmp/{title}.jpg"
    img.save(path)
    return path

# ================================
# SORTIERUNG
# ================================

def categorize(data, title, genre):
    for g in genre.split(","):
        data["categories"].setdefault(g.strip(), []).append(title)

# ================================
# UI
# ================================

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_buttons(chat_id, text, buttons):
    requests.post(f"{URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons}
    })

def show_home(chat_id):
    send_buttons(chat_id, "🎬 Library", [
        [{"text": "🎬 Genres", "callback_data": "genres"}]
    ])

def show_genres(chat_id, data):
    buttons = [[{"text": g, "callback_data": f"genre_{g}"}] for g in data["categories"]]
    send_buttons(chat_id, "Genres:", buttons)

def show_movies(chat_id, movies):
    buttons = [[{"text": m, "callback_data": f"movie_{m}"}] for m in movies]
    send_buttons(chat_id, "Filme:", buttons)

# ================================
# FILM CARD
# ================================

def send_film_card(chat_id, movie, file_id, user_id):
    title = movie["Title"]
    genre = movie["Genre"]

    plot_raw = movie.get("Plot", "")
    short, plot = generate_story(title, plot_raw, genre, user_id)

    caption = f"""🎬 {title.upper()} ({movie["Year"]})
🔥 {genre}
━━━━━━━━━━━━━━
⭐ {movie["imdbRating"]} • ⏱ {movie["Runtime"]}
🎥 {movie["Director"]}
━━━━━━━━━━━━━━
🧠 {short}

📖 STORY
{plot}
━━━━━━━━━━━━━━"""

    # Poster
    if movie["Poster"] != "N/A":
        requests.post(f"{URL}/sendPhoto", json={"chat_id": chat_id, "photo": movie["Poster"]})
    else:
        path = create_banner(title)
        with open(path, "rb") as img:
            requests.post(f"{URL}/sendPhoto", files={"photo": img}, data={"chat_id": chat_id})

    # Video
    requests.post(f"{URL}/sendVideo", json={
        "chat_id": chat_id,
        "video": file_id,
        "caption": caption
    })

# ================================
# VIDEO UPLOAD
# ================================

def handle_video(message):
    data = load_data()

    video = message.get("video") or message.get("document")
    chat_id = message["chat"]["id"]
    title = message.get("caption", "Unknown")

    movie = get_movie(title)
    if not movie:
        send_message(chat_id, "❌ Film nicht gefunden")
        return

    data["movies"].append({
        "title": movie["Title"],
        "file_id": video["file_id"],
        "genre": movie["Genre"]
    })

    categorize(data, movie["Title"], movie["Genre"])
    save_data(data)

    # 👉 an User senden
    send_film_card(chat_id, movie, video["file_id"], chat_id)

    # 👉 in Kanal senden
    send_film_card(CHANNEL, movie, video["file_id"], chat_id)

# ================================
# SHOW MOVIE
# ================================

def show_movie(chat_id, title):
    data = load_data()
    m = next((x for x in data["movies"] if x["title"] == title), None)
    if not m:
        return

    movie = get_movie(title)
    if not movie:
        return

    send_film_card(chat_id, movie, m["file_id"], chat_id)

# ================================
# WEBHOOK
# ================================

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        data_cb = update["callback_query"]["data"]
        data = load_data()

        if data_cb == "genres":
            show_genres(chat_id, data)

        elif data_cb.startswith("genre_"):
            show_movies(chat_id, data["categories"].get(data_cb.replace("genre_", ""), []))

        elif data_cb.startswith("movie_"):
            show_movie(chat_id, data_cb.replace("movie_", ""))

        return "ok"

    message = update.get("message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]

    if "text" in message and message["text"] == "/start":
        show_home(chat_id)

    elif "video" in message or "document" in message:
        handle_video(message)

    return "ok"

@app.route("/")
def home():
    return "Bot läuft 🚀"

# ================================
# START
# ================================

if __name__ == "__main__":
    webhook_url = os.getenv("WEBHOOK_URL")
    requests.get(f"{URL}/setWebhook?url={webhook_url}/webhook/{TOKEN}")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)