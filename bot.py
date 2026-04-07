# ================================
# 🎬 STABILER TELEGRAM BOT (NO AI)
# ================================

import os, json
from telegram import *
from telegram.ext import *
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

DATA_FILE = "data.json"

# ---------------- DATA ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"movies": []}


def save_data(data):
    json.dump(data, open(DATA_FILE, "w"))


data = load_data()

# ---------------- ADD MOVIE ----------------
def add_movie(title, year, file_id):
    new_id = max([m.get("id", 0) for m in data["movies"]] + [0]) + 1

    data["movies"].append({
        "id": new_id,
        "title": title,
        "year": year,
        "file_id": file_id
    })

    save_data(data)


# ---------------- SEARCH ----------------
def search_movies(query):
    return [m for m in data["movies"] if query.lower() in m["title"].lower()]


# ---------------- START ----------------
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("📤 Upload", callback_data="upload")],
        [InlineKeyboardButton("🔍 Suche", callback_data="search")]
    ]

    await update.message.reply_text(
        "🎬 *Library of Legends*\n\nSchick mir ein Video!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ---------------- VIDEO ----------------
async def handle_video(update, context):
    msg = update.message
    video = msg.video or msg.document

    title = msg.caption if msg.caption else "Unknown"

    add_movie(title, 2025, video.file_id)

    await msg.reply_text("✅ Film gespeichert!")


# ---------------- TEXT SEARCH ----------------
async def handle_text(update, context):
    query = update.message.text.strip()

    results = search_movies(query)

    if not results:
        await update.message.reply_text("❌ Kein Film gefunden")
        return

    text = "🎬 Ergebnisse:\n\n"

    for m in results:
        text += f"{m['title']} ({m['year']})\n"

    await update.message.reply_text(text)


# ---------------- BUTTON ----------------
async def button(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "search":
        await query.edit_message_text("🔍 Schreib den Filmnamen")


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
    return "🤖 Bot läuft!"


# ---------------- START ----------------
if __name__ == "__main__":
    import asyncio

    asyncio.run(application.bot.set_webhook(f"{WEBHOOK_URL}/webhook/{TOKEN}"))

    app.run(host="0.0.0.0", port=8080)