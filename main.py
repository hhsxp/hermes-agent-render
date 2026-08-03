import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGER ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- WEBSERVER ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_web():
    srv = HTTPServer(("0.0.0.0", PORT), Handler)
    logger.info(f"Webserver rodando na porta {PORT}")
    srv.serve_forever()

# --- INTEGRAÇÃO TELEGRAM ---
def call_llm(prompt):
    import requests
    headers = {
        "Authorization": "Bearer sk-or-...",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://seusite.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "google/gemini-2.0-flash",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Erro: {r.status_code}"

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Iniciando Hermes Agent...")

    # Webserver em background
    threading.Thread(target=run_web, daemon=True).start()
    time.sleep(1)

    # Telegram (main thread obrigatório)
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    app = Application.builder().token(TOKEN).build()

    async def start(update, ctx):
        await update.message.reply_text("🤖 Online!")

    async def handle_msg(update, ctx):
        reply = call_llm(update.message.text)
        await update.message.reply_text(reply)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    logger.info("🤖 Telegram pronto.")
    app.run_polling()
