import os
import logging
from flask import Flask, request
from dotenv import load_dotenv
import requests
import threading, time, requests

def keepalive():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com")
        except:
            pass
        time.sleep(25 * 60)  # pinga a cada 25 minutos

threading.Thread(target=keepalive, daemon=True).start()

# --- Carrega variáveis ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WEBHOOK_PATH = f"/{TOKEN}"

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask ---
app = Flask(__name__)

# --- Função para chamar LLM via OpenRouter ---
def call_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "meta-llama/llama-4-maverick:free",  # grátis
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente útil e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Erro na API ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        return f"Falha na conexão: {str(e)}"

# --- Rotas Flask ---
@app.route("/")
def index():
    return "🤖 Hermes Agent Online!"

@app.route("/8872193272:AAHhJQi1eQInSBdi6RsGjqDZd754whG64UE", methods=["GET", "POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        # Responde
        answer = call_openrouter(text)

        # Envia resposta
        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(send_url, json={"chat_id": chat_id, "text": answer})

        logger.info(f"[{chat_id}] {text} → {answer[:50]}...")
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

# --- Configura webhook ---
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    full_url = f"https://hermes-agent-render.onrender.com{WEBHOOK_PATH}"
    r = requests.post(url, json={"url": full_url})
    if r.status_code == 200:
        logger.info(f"✅ Webhook configurado: {full_url}")
    else:
        logger.warning(f"❌ Erro ao configurar webhook: {r.text}")

# --- Inicializa ---
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
