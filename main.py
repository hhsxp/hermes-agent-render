import os
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN", "8872193272:***")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "***")
PORT = int(os.environ.get("PORT", 10000))

# --- LOGGER ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SERVIDOR HTTP ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass

def run_keepalive_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"🌐 Servidor HTTP rodando na porta {PORT}")
    server.serve_forever()

# --- HANDLERS ---
async def start(update, context):
    await update.message.reply_text(
        "🤖 Hermes Agent Online!\nEnvie qualquer mensagem."
    )

async def handle_message(update, context):
    msg = update.message.text
    response = call_openrouter(msg)
    await update.message.reply_text(response)

# --- LLM ---
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
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {"role": "system", "content": "Você é Hermes, assistente inteligente e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Erro na API: {r.status_code}"
    except Exception as e:
        return f"Falha: {e}"

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Iniciando Hermes Agent...")

    # Start keepalive HTTP server in background
    threading.Thread(target=run_keepalive_server, daemon=True).start()
    time.sleep(1)

    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot Telegram iniciado!")
    app.run_polling()
