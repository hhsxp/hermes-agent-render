import os
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- CONFIGURAÇÕES INICIAIS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# --- INICIALIZAÇÕES ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SERVIDOR KEEPALIVE (Render exige) ---
class HealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_keepalive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthServer)
    server.serve_forever()

# --- FUNÇÃO GENÉRICA: chamar LLM via OpenRouter ---
def ask_llm(message):
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )
    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-maverick:free",
            messages=[{"role": "user", "content": message}],
            max_tokens=1024
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}")
        return "Erro no modelo de linguagem."

# --- ROTINAS POR PLATAFORMA ---
def start_telegram():
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        resposta = ask_llm(update.message.text)
        await update.message.reply_text(str(resposta))

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

def start_discord():
    if DISCORD_TOKEN:
        import discord
        intents = discord.Intents.default()
        intents.messages = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print(f"[Discord] Bot conectado como {client.user}")

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return
            if message.content.startswith("!hermes"):
                prompt = message.content[7:].strip()
                resposta = ask_llm(prompt)
                await message.channel.send(str(resposta))

        client.run(DISCORD_TOKEN)

# --- MAIN ---
if __name__ == "__main__":
    threading.Thread(target=run_keepalive, daemon=True).start()

    if TELEGRAM_TOKEN:
        threading.Thread(target=start_telegram, daemon=True).start()
    if DISCORD_TOKEN:
        threading.Thread(target=start_discord, daemon=True).start()

    print("Agente rodando. Aguardando mensagens...")
    while True:
        pass
