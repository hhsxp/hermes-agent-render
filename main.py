import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "8872193272:***")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-...")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGER ---
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- KEEPALIVE ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, fmt, *args):
        pass

def run_webserver():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    logger.info(f"🌐 Webserver na porta {PORT}")
    server.serve_forever()

# --- BOT ---
def call_openrouter(prompt):
    import requests
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "google/gemini-2.0-flash",
        "messages": [
            {"role": "system", "content": "Você é Hermes, assistente inteligente e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"⚠️ Erro da API: {r.status_code}"
    except Exception as e:
        return f"❌ Falha: {e}"

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Iniciando Hermes Agent...")

    # Webserver em background
    threading.Thread(target=run_webserver, daemon=True).start()
    time.sleep(2)

    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    app = Application.builder().token(TOKEN).build()

    # Handlers
    async def start(update, ctx):
        await update.message.reply_text("🤖 Hermes Agent online! Envie uma mensagem.")

    async def handle_msg(update, ctx):
        msg = update.message.text
        reply = call_openrouter(msg)
        await update.message.reply_text(reply)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    logger.info("🤖 Bot Telegram pronto!")
    app.run_polling()
