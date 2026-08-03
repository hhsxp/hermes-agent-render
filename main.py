# main.py
import os
import logging
import threading
from dotenv import load_dotenv

# Carrega variáveis do .env ou do ambiente do Render
load_dotenv()

from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import discord
from discord import Intents

# ========================
# CONFIGURAÇÕES (coloque essas no painel do Render)
# ========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-...")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "887...")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

MODELS = [
    "google/gemini-2.0-flash",  # grátis e bom
    "meta-llama/llama-4-maverick",
    "google/gemini-2.0-flash-thinking"
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

# ========================
# FUNÇÃO PARA CHAMAR O LLM
# ========================
async def ask_llm(prompt):
    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.warning(f"Modelo {model} falhou: {e}")
    return "⚠️ Todos os modelos falharam."

# ========================
# INTEGRAÇÃO TELEGRAM
# ========================
async def start(update: Update, context):
    await update.message.reply_text("🤖 Hermes online! Pergunte algo.")

async def handle_message(update: Update, context):
    msg = update.message.text
    resposta = await ask_llm(msg)
    await update.message.reply_text(resposta)

def run_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

# ========================
# INTEGRAÇÃO DISCORD
# ========================
intents = Intents.default()
intents.messages = True

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'[DISCORD] Logado como {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content.startswith('!hermes'):
            prompt = message.content.replace('!hermes', '').strip()
            resposta = await ask_llm(prompt)
            await message.channel.send(resposta)

def run_discord():
    client_dc = MyClient(intents=intents)
    client_dc.run(DISCORD_TOKEN)

# ========================
# LOOP KEEPALIVE PARA O RENDER
# ========================
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hermes Gateway Online")

def start_webserver():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Inicia o servidor web (necessário pro Render manter o container ativo)
    threading.Thread(target=start_webserver, daemon=True).start()

    # Inicia os serviços em paralelo
    t_telegram = threading.Thread(target=run_telegram)
    t_discord = threading.Thread(target=run_discord)

    t_telegram.start()
    if DISCORD_TOKEN:
        t_discord.start()

    t_telegram.join()
