import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "8872193272:***")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "MTUz...")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "***")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGER ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- SERVIDOR HTTP (para manter alive no Render) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # Silencia logs do servidor HTTP

def run_keepalive_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"🌐 Servidor HTTP rodando na porta {PORT}")
    server.serve_forever()

# --- HANDLERS DO TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Hermes Agent Online!\n"
        "Envie qualquer mensagem que eu respondo com ajuda de uma IA.\n\n"
        "/help - Ver comandos disponíveis"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Comandos disponíveis:\n"
        "/start - Iniciar conversa\n"
        "/help - Mostrar esta ajuda\n\n"
        "Qualquer outra mensagem será processada pela IA."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    # Chama OpenRouter
    response = call_openrouter(user_msg)

    await update.message.reply_text(response)

# --- INTEGRAÇÃO COM OPENROUTER ---
def call_openrouter(prompt: str) -> str:
    import requests

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent",
    }
    payload = {
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente e educado."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Erro na API ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        return f"Falha na conexão: {e}"

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Iniciando Hermes Agent...")

    # Inicia servidor keepalive em background
    Thread = threading.Thread(target=run_keepalive_server, daemon=True)
    Thread.start()

    # Configura e inicia bot do Telegram no main thread com asyncio
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("🤖 Bot Telegram iniciado!")
        await app.run_polling()

    loop.run_until_complete(run())
