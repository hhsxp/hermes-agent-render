import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis do ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ========================
# Servidor Keepalive HTTP (necessário pro Render manter o serviço ativo)
# ========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"✅ Hermes Agent Online!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Silencia logs HTTP

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"Servidor HTTP rodando na porta {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Erro no servidor HTTP: {e}")

# ========================
# Bot do Telegram + OpenRouter
# ========================
def start_telegram_bot():
    if not TELEGRAM_TOKEN:
        logger.warning("Token do Telegram não definido.")
        return

    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    import requests

    async def handle_message(update: Update, context):
        user_msg = update.message.text
        logger.info(f"[Telegram] Mensagem recebida: {user_msg}")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hermes-agent-render.onrender.com",
            "X-Title": "Hermes Agent"
        }

        payload = {
            "model": "google/gemini-2.0-flash",
            "messages": [
                {"role": "system", "content": "Você é um assistente útil chamado Hermes."},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": 1000
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                reply = result["choices"][0]["message"]["content"]
            else:
                reply = f"⚠️ Erro na API ({response.status_code}): {response.text[:100]}"
        except Exception as e:
            reply = f"❌ Exception: {e}"
            logger.error(reply)

        await update.message.reply_text(reply)

    async def start(update: Update, context):
        await update.message.reply_text("🤖 Hermes online! Envie sua pergunta.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot do Telegram iniciado...")
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app.run_polling()

# ========================
# Main
# ========================
if __name__ == "__main__":
    logger.info("Iniciando Hermes Agent...")

    # Start HTTP server em background (keepalive)
    threading.Thread(target=start_http_server, daemon=True).start()

    # Start Telegram bot
    threading.Thread(target=start_telegram_bot, daemon=True).start()

    logger.info("Hermes Agent pronto. Aguardando mensagens...")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Encerrando...")
