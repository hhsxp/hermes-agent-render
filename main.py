import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import threading
import requests

# --- CONFIGURAÇÕES ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://hermes-agent-render.onrender.com/webhook")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FLASK APP ---
app = Flask(__name__)

# --- INICIALIZA BOT ---
bot_app = ApplicationBuilder().token(TOKEN).build()

async def start(update, context):
    await update.message.reply_text("🤖 Hermes online! Pergunte algo.")

async def handle_message(update, context):
    msg = update.message.text
    answer = call_openrouter(msg)
    await update.message.reply_text(answer)

# Registrando handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- ROTAS FLASK ---
@app.route("/")
def index():
    return "🤖 Hermes Agent Online!"

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.create_task(bot_app.process_update(update))
    return "OK", 200

@app.route("/healthz")
def health():
    return "OK", 200

if __name__ == "__main__":
    import asyncio

    async def setup_webhook():
        await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())

    logger.info("🤖 Webhook configurado!")
    app.run(host="0.0.0.0", port=PORT)
