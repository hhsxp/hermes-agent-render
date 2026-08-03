import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, fmt, *args):
        pass

def start_keepalive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Keepalive server rodando na porta {port}")
    server.serve_forever()

# Inicia o HTTP server em background
threading.Thread(target=start_keepalive, daemon=True).start()

# Importa e roda o Telegram BOT no THREAD PRINCIPAL
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests

async def handle_message(update: Update, context):
    question = update.message.text
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente útil e educado."},
            {"role": "user", "content": question}
        ],
        "max_tokens": 1000
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            answer = data["choices"][0]["message"]["content"]
        else:
            answer = f"Erro no modelo: {r.status_code}"
    except Exception as e:
        answer = f"Erro de conexão: {str(e)}"

    await update.message.reply_text(answer)

async def start(update: Update, context):
    await update.message.reply_text("🤖 Hermes online! Pergunte algo.")

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

logger.info("🤖 Bot Telegram iniciado no thread principal...")
app.run_polling()
