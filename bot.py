# ================================
# 🎬 ULTIMATE NETFLIX BOT (FINAL)
# ================================

import os, json, requests
from telegram import *
from telegram.ext import *
from flask import Flask, request
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

DATA_FILE = "data.json"
USER_FILE = "users.json"
PROFILE_FILE = "profiles.json"

# ---------------- DATA ----------------
def load_json(file, default):
    if os.path.exists(file):
        return json.load(open(file))
    return default

def save_json(file, data):
    json.dump(data, open(file,"w"))

data = load_json(DATA_FILE, {"movies": []})
users = load_json(USER_FILE, {})
profiles = load_json(PROFILE_FILE, {})

# ---------------- MOVIE ADD ----------------
def add_movie(title, year, file_id):
    new_id = max([m.get("id",0) for m in data["movies"]] + [0]) + 1
    data["movies"].append({
        "id": new_id,
        "title": title,
        "year": year,
        "file_id": file_id
    })
    save_json(DATA_FILE, data)

# ---------------- SEARCH ----------------
def search_movies(q):
    return [m for m in data["movies"] if q.lower() in m["title"].lower()]

# ---------------- PROFILE ----------------
def get_profile(user_id, context):
    return context.user_data.get("profile")

# ---------------- HANDLERS ----------------
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🎬 Upload", callback_data="upload")],
        [InlineKeyboardButton("🔍 Suche", callback_data="search")],
        [InlineKeyboardButton("👤 Profile", callback_data="profiles")],
        [InlineKeyboardButton("🧠 KI Empfehlungen", callback_data="ai")]
    ]

    await update.message.reply_text(
        "🎬 *Library of Legends*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------------- VIDEO ----------------
async def handle_video(update, context):
    video = update.message.video or update.message.document
    title = update.message.caption or "Unknown"

    add_movie(title, 2025, video.file_id)

    await update.message.reply_text("✅ Gespeichert!")

# ---------------- SEARCH ----------------
async def handle_text(update, context):
    q = update.message.text
    results = search_movies(q)

    if not results:
        await update.message.reply_text("❌ Nichts gefunden")
        return

    text = "🎬 Ergebnisse:\n\n"
    for m in results:
        text += f"{m['title']} ({m['year']})\n"

    await update.message.reply_text(text)

# ---------------- AI ----------------
async def ai_reco(update, context):
    movies = [m["title"] for m in data["movies"]][-5:]

    if not movies:
        await update.callback_query.edit_message_text("❌ Keine Daten")
        return

    prompt = f"Empfehle Filme basierend auf: {', '.join(movies)}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    await update.callback_query.edit_message_text(res.choices[0].message.content)

# ---------------- BUTTON ----------------
async def button(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "ai":
        await ai_reco(update, context)

    elif q.data == "search":
        await q.edit_message_text("🔍 Schreib Filmnamen")

# ---------------- WEBHOOK ----------------
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot läuft!"

if __name__ == "__main__":
    import asyncio
    asyncio.run(application.bot.set_webhook(f"{WEBHOOK_URL}/webhook/{TOKEN}"))
    app.run(host="0.0.0.0", port=8080)