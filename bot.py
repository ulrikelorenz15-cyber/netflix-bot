# ================================
# 🎬 NETFLIX BOT FINAL (MENU + UI FINAL + ULTRA MATCH + AUTO DB + NETFLIX UI)
# ================================

import os
import json
import requests
from flask import Flask, request
from openai import OpenAI
from difflib import get_close_matches

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL = "-1003526259129"
OMDB_KEY = "a3776f86"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_FILE = "data.json"
CACHE = {}
SESSION = {}

# ================================
# UTILS
# ================================

def log_error(e):
    print("ERROR:", str(e))

def safe_post(method, payload):
    try:
        requests.post(f"{URL}/{method}", json=payload, timeout=5)
    except Exception as e:
        log_error(e)

def clean_title(raw):
    if not raw:
        return ""
    raw = raw.replace(".", " ")
    blacklist = ["1080p","720p","bluray","x264","x265","dvdrip","webdl"]
    return " ".join([w for w in raw.split() if w.lower() not in blacklist])

# ================================
# 🧠 AUTO DB (NEU)
# ================================

AUTO_DB = {
    "bourne identität": "The Bourne Identity",
    "bourne": "The Bourne Identity",
    "jurassic": "Jurassic Park",
    "havoc": "Havoc",
    "godfather": "The Godfather",
    "shawshank": "The Shawshank Redemption"
}

def auto_db_match(title):
    t = title.lower()
    for key in AUTO_DB:
        if key in t:
            return AUTO_DB[key]
    return None

# ================================
# 🧠 FUZZY MATCH
# ================================

def fuzzy_match(title, data):
    titles = [m["title"] for m in data["movies"]]
    match = get_close_matches(title, titles, n=1, cutoff=0.6)
    return match[0] if match else None

# ================================
# 🧠 AI DETECT
# ================================

def ai_detect_title(raw_text):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"Errate den Film Titel:\n{raw_text}\nNur Titel."
            }],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except:
        return None

# ================================
# 🧠 MULTI TRY
# ================================

def try_multiple_titles(title):
    variants = [
        title,
        title.split("(")[0],
        title.split("-")[0],
        " ".join(title.split(" ")[:2])
    ]

    for t in variants:
        movie = get_movie(t.strip())
        if movie:
            return movie
    return None

# ================================
# 🎞 NETFLIX ROW SYSTEM (NEU)
# ================================

def show_row(chat_id, title, movies):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": f"━━━ {title} ━━━"
    })

    buttons = []
    for m in movies[:5]:
        buttons.append({
            "text": m["title"][:15],
            "callback_data": f"movie_{m['title']}"
        })

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": " ",
        "reply_markup": {"inline_keyboard": [buttons]}
    })

# ================================
# 🏆 TOP SYSTEM (NEU)
# ================================

def get_top_movies(data):
    return sorted(
        data["movies"],
        key=lambda x: x.get("views", 0),
        reverse=True
    )[:10]

# ================================
# MAIN MENU
# ================================

def show_main_menu(chat_id):
    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n\nWähle eine Kategorie:",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "▶️ Start", "callback_data": "home"}],
                [{"text": "🔥 Trending", "callback_data": "menu_trending"}],
                [{"text": "🆕 Neu", "callback_data": "menu_new"}],
                [{"text": "🎞 Reihen", "callback_data": "menu_series"}]
            ]
        }
    })

# ================================
# LOCAL MATCH
# ================================

LOCAL_DB = {
    "bourne": "The Bourne Identity",
    "jurassic": "Jurassic Park"
}

def local_match(title):
    t = title.lower()
    for key in LOCAL_DB:
        if key in t:
            return LOCAL_DB[key]
    return None

# ================================
# OMDb
# ================================

def get_movie(title):
    if title in CACHE:
        return CACHE[title]

    try:
        r = requests.get(
            f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}",
            timeout=5
        ).json()

        if r.get("Response") == "False":
            return None

        CACHE[title] = r
        return r
    except:
        return None

# ================================
# DATA
# ================================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return json.load(open(DATA_FILE))
        except:
            return {"movies": []}
    return {"movies": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))

def get_next_id(data):
    return str(len(data["movies"]) + 1).zfill(4)

# ================================
# RANKING
# ================================

def get_rankings(data):
    movies = data["movies"]

    return {
        "🔥 Trending": sorted(movies, key=lambda x: x.get("views", 0), reverse=True)[:10],
        "🆕 Neu": list(reversed(movies))[:10]
    }

# ================================
# SERIES
# ================================

def detect_series(title):
    t = title.lower()
    if "bourne" in t:
        return "Bourne"
    if "jurassic" in t:
        return "Jurassic"
    return None

def get_series_list(data, name):
    return [m for m in data["movies"] if m.get("series") == name]

# ================================
# HOME (UPGRADE)
# ================================

def show_home(chat_id):
    data = load_data()

    safe_post("sendMessage", {
        "chat_id": chat_id,
        "text": "🎬 Library of Legends\n🔥 Netflix Style"
    })

    show_row(chat_id, "🔥 Trending", get_rankings(data)["🔥 Trending"])
    show_row(chat_id, "🆕 Neu", get_rankings(data)["🆕 Neu"])
    show_row(chat_id, "🏆 Top", get_top_movies(data))

    show_series_row(chat_id, data)

# ================================
# VIDEO (ULTRA MATCH UPGRADE)
# ================================

def handle_video(msg):
    data = load_data()
    video = msg.get("video") or msg.get("document")

    raw = clean_title(msg.get("caption") or "")
    movie = None

    # 1 LOCAL
    if raw:
        local = local_match(raw)
        if local:
            movie = try_multiple_titles(local)

    # 1.5 AUTO DB (NEU)
    if not movie and raw:
        auto = auto_db_match(raw)
        if auto:
            movie = try_multiple_titles(auto)

    # 2 NORMAL
    if not movie and raw:
        movie = try_multiple_titles(raw)

    # 3 FUZZY
    if not movie and raw:
        fuzzy = fuzzy_match(raw, data)
        if fuzzy:
            movie = get_movie(fuzzy)

    # 4 AI
    if not movie and raw:
        ai_title = ai_detect_title(raw)
        if ai_title:
            movie = try_multiple_titles(ai_title)

    if not movie:
        safe_post("sendMessage", {
            "chat_id": msg["chat"]["id"],
            "text": f"❌ Nicht erkannt: {raw}"
        })
        return

    entry = {
        "id": get_next_id(data),
        "title": movie["Title"],
        "file_id": video["file_id"],
        "views": 0,
        "series": detect_series(movie["Title"])
    }

    data["movies"].append(entry)
    save_data(data)

    safe_post("sendMessage", {
        "chat_id": msg["chat"]["id"],
        "text": f"🧠 Erkannt: {movie['Title']}"
    })

    send_card(msg["chat"]["id"], movie, entry)
    send_card(CHANNEL, movie, entry)