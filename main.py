import os
import logging
import threading
import time
import requests
from flask import Flask, request

# --- Configurações ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = f"https://hermes-agent-render-21ab.onrender.com/webhook"

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask app ---
app = Flask(__name__)

# --- Keepalive (evita dormência do Render) ---
def keepalive():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com")
        except:
            pass
        time.sleep(25 * 60)

threading.Thread(target=keepalive, daemon=True).start()

# --- Chamada ao LLM (OpenRouter grátis) ---
def call_llm(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render-21ab.onrender.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.7
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Erro OpenRouter: {r.status_code} - {r.text[:200]}")
            return f"Erro na API ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        logger.error(f"Falha na LLM: {str(e)}")
        return f"Falha na conexão: {str(e)}"

# --- Rotas Flask ---
@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        answer = call_llm(text)

        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(send_url, json={"chat_id": chat_id, "text": answer})

        logger.info(f"[{chat_id}] {text} → {answer[:50]}...")
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

# --- Configura webhook no início ---
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    r = requests.post(url, json={"url": WEBHOOK_URL})
    if r.status_code == 200:
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
    else:
        logger.warning(f"❌ Erro ao configurar webhook: {r.text}")

# --- Inicializa ---
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
