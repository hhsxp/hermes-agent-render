# main.py - Hermes Agent via Telegram no Render
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURAÇÕES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8872193272:AAFW8jvgIKtbSF8GNSIW-yz6I8hmb-wYfcI")

# --- LOGGER ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SERVIDOR KEEPALIVE (Render exige) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hermes Agent Online!")

    def log_message(self, format, *args):
        pass  # Silencia logs do servidor HTTP

def start_keepalive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Keepalive server rodando na porta {port}")
    server.serve_forever()

# --- HANDLERS DO TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Olá! Sou o Hermes Agent!\n"
        "Envie qualquer mensagem que eu respondo com ajuda de uma IA via OpenRouter.\n\n"
        "Digite /help para ver comandos."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Comandos disponíveis:\n"
        "/start - Iniciar conversa\n"
        "/help - Mostrar este menu\n"
        "Qualquer outra mensagem - Pergunte algo!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    logger.info(f"Mensagem recebida: {user_msg}")

    resposta = call_ollama(user_msg)

    await update.message.reply_text(str(resposta))

# --- INTEGRAÇÃO COM OPENROUTER ---
def call_openrouter(prompt):
    import requests
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent (Telegram)"
    }
    payload = {
        "model": "google/gemini-2.0-flash",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente e gentil. Responda de forma clara e objetiva."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Erro OpenRouter [{response.status_code}]: {response.text}")
            return "Desculpe, não consegui processar sua solicitação agora."
    except Exception as e:
        logger.error(f"Exceção ao chamar OpenRouter: {e}")
        return "Ocorreu um erro ao tentar falar com o modelo de linguagem."

# Alias para uso interno
call_ollama = call_openrouter  # Compatibilidade com chamadas antigas

# --- MAIN ---
if __name__ == "__main__":
    # Inicia o servidor keepalive em background
    Thread(target=start_keepalive_server, daemon=True).start()

    # Inicia o bot do Telegram
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Hermes Agent iniciado via Telegram...")
    print("🤖 Hermes Agent iniciado via Telegram...")

    # Roda o polling
    app.run_polling()
