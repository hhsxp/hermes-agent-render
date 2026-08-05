import os
import logging
import threading
import time
from flask import Flask, request
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGER ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- FLASK APP ---
app = Flask(__name__)

# --- FUNÇÃO PARA CHAMAR O MODELO GRATUITO ---
def call_llm(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://seusite.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ Erro na API: {r.status_code} - {r.text[:200]}"
    except Exception as e:
        return f"❌ Falha na conexão: {str(e)}"

# --- HANDLERS DO TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Hermes Agent online!\n"
        "Digite algo e eu respondo com ajuda de uma IA.\n\n"
        "/help - Ver comandos disponíveis"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Digite qualquer mensagem e eu respondo!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    logger.info(f"[MSG RECEIVED] User: {user_input}")
    response = call_llm(user_input)
    await update.message.reply_text(response)

# --- WEB SERVER (Flask) ---
@app.route("/")
def index():
    return "<h1>🤖 Hermes Agent Online</h1>", 200

@app.route("/health")
def health():
    return "OK", 200

# --- ROTAS WEBHOOK ---
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    update_queue.put(update)
    return "OK", 200

# --- INICIALIZAÇÃO DO BOT ---
bot_app = Application.builder().token(TOKEN).build()
update_queue = bot_app.update_queue
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_cmd))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- MAIN ---
if __name__ == "__main__":
    # Inicia o bot em thread separada
    def start_bot():
        bot_app.run_polling()

    threading.Thread(target=start_bot, daemon=True).start()

    # Inicia web server Flask
    logger.info("🌐 Webserver online!")
    app.run(host="0.0.0.0", port=PORT)
