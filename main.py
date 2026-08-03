import os
import logging
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# Logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8872193272:***")

# ========================
# Servidor keepalive HTTP (necessário pro Render manter o serviço ativo)
# ========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass

def start_keepalive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Servidor keepalive rodando na porta {port}")
    server.serve_forever()

# ========================
# Bot Telegram + OpenRouter
# ========================
def run_bot():
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    import requests

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-...49e7")
    MODEL = "google/gemini-2.0-flash"

    async def call_openrouter(prompt):
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hermes-agent-render.onrender.com",
            "X-Title": "Hermes Agent"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Você é Hermes, um assistente útil e educado."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000
        }
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return "Desculpe, não consegui processar sua requisição."
        except Exception as e:
            logger.error(f"Erro ao chamar OpenRouter: {e}")
            return "Erro interno."

    async def handle_message(update, context):
        user_msg = update.message.text
        logger.info(f"[{update.effective_user.first_name}] {user_msg}")

        reply = await call_openrouter(user_msg)
        await update.message.reply_text(reply)

    async def start(update, context):
        await update.message.reply_text("🤖 Hermes online! Me envie qualquer mensagem.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ✅ Força o evento loop manualmente (corrige o erro do Python 3.14)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app.run_polling()

# ========================
# Main
# ========================
if __name__ == "__main__":
    Thread(target=start_keepalive, daemon=True).start()
    run_bot()
