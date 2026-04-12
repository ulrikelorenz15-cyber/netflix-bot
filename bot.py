# ================================
# 🎬 FINAL TELEGRAM NETFLIX BOT
# ================================

import sqlite3
import re
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "DEIN_BOT_TOKEN"
TMDB_KEY = ""  # optional

DB = "movies.db"

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
        category TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ================================
# PARSER
# ================================

def parse_caption(caption):
    if not caption:
        return "Film", "-", "General"

    title_match = re.search(r"🎬\s*(.*?)\s*\(", caption)
    title = title_match.group(1) if title_match else caption.split("\n")[0]

    story_match = re.search(r"STORY\s*(.*?)\s*(▶️|#|$)", caption, re.S)
    story = story_match.group(1).strip() if story_match else "-"

    tags = re.findall(r"#(\w+)", caption)
    category = tags[0] if tags else "General"

    return title, story, category

# ================================
# SAVE MOVIE
# ================================

def save_movie(msg):
    if not msg.video:
        return

    title, story, category = parse_caption(msg.caption or "")

    con = db()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO movies VALUES(?,?,?,?,?)
    """, (
        str(int(time.time())),
        title,
        story,
        msg.video.file_id,
        category
    ))

    con.commit()
    con.close()

# ================================
# START MENU
# ================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Filme", callback_data="movies")],
        [InlineKeyboardButton("📂 Kategorien", callback_data="categories")],
        [InlineKeyboardButton("🔍 Suche", callback_data="search")]
    ]

    await update.message.reply_text(
        "🎬 *Netflix Bot*\nWähle:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================================
# SHOW MOVIES
# ================================

async def show_movies(update, context):
    con = db()
    cur = con.cursor()

    movies = cur.execute("SELECT * FROM movies ORDER BY id DESC").fetchall()
    con.close()

    for m in movies[:10]:
        keyboard = [
            [InlineKeyboardButton("▶️ Abspielen", callback_data=f"play_{m[0]}")]
        ]

        await update.effective_chat.send_message(
            f"🎬 *{m[1]}*\n\n{m[2]}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ================================
# PLAY
# ================================

async def play_movie(update, context, movie_id):
    con = db()
    cur = con.cursor()

    m = cur.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
    con.close()

    if m:
        await update.effective_chat.send_video(
            video=m[3],
            caption=f"🎬 {m[1]}"
        )

# ================================
# CATEGORIES
# ================================

async def show_categories(update, context):
    con = db()
    cur = con.cursor()

    cats = cur.execute("SELECT DISTINCT category FROM movies").fetchall()
    con.close()

    keyboard = [
        [InlineKeyboardButton(c[0], callback_data=f"cat_{c[0]}")]
        for c in cats
    ]

    await update.effective_chat.send_message(
        "📂 Kategorien:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================================
# CATEGORY VIEW
# ================================

async def show_category(update, context, cat):
    con = db()
    cur = con.cursor()

    movies = cur.execute("SELECT * FROM movies WHERE category=?", (cat,)).fetchall()
    con.close()

    for m in movies[:10]:
        keyboard = [
            [InlineKeyboardButton("▶️ Abspielen", callback_data=f"play_{m[0]}")]
        ]

        await update.effective_chat.send_message(
            f"🎬 {m[1]}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ================================
# SEARCH
# ================================

async def search_prompt(update, context):
    context.user_data["search"] = True
    await update.effective_chat.send_message("🔍 Suchbegriff eingeben:")

async def search_handler(update, context):
    if not context.user_data.get("search"):
        return

    query = update.message.text.lower()

    con = db()
    cur = con.cursor()

    movies = cur.execute("SELECT * FROM movies").fetchall()
    con.close()

    results = [m for m in movies if query in m[1].lower()]

    for m in results[:10]:
        await update.message.reply_text(f"🎬 {m[1]}")

    context.user_data["search"] = False

# ================================
# CALLBACK
# ================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "movies":
        await show_movies(update, context)

    elif data == "categories":
        await show_categories(update, context)

    elif data == "search":
        await search_prompt(update, context)

    elif data.startswith("play_"):
        await play_movie(update, context, data.split("_")[1])

    elif data.startswith("cat_"):
        await show_category(update, context, data.split("_")[1])

# ================================
# HANDLER
# ================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.VIDEO, lambda u,c: save_movie(u.message)))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

print("✅ BOT LÄUFT...")
app.run_polling()