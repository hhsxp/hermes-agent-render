import os
import logging
import threading
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv

# --- Carrega variáveis ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask ---
app = Flask(__name__)

# --- Keepalive (pinga o servidor a cada 25 min) ---
def keepalive():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com")
        except:
            pass
        time.sleep(25 * 60)

threading.Thread(target=keepalive, daemon=True).start()

# --- Função para chamar Groq ---
def call_ia(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Erro na API: {r.status_code} - {r.text[:200]}"
    except Exception as e:
        return f"Falha na conexão: {str(e)}"

# --- Rotas Flask ---
@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        answer = call_ia(text)
        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={answer}"
        requests.get(send_url)
        logger.info(f"[{chat_id}] {text} → {answer[:50]}...")
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

# --- Inicializa ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
