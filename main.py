import os
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def call_llm(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://hermes-agent-render-21ab.onrender.com",
        "X-Title": "Hermes Bot"
    }
    data = {
        "model": "nousresearch/tailwind-v1.5b:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Erro OpenRouter: {r.status_code} - {r.text[:200]}")
            return f"Erro na API ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        logger.error(f"Falha na LLM: {str(e)}")
        return f"Falha na conexão: {str(e)}"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {str(e)}")

@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        logger.info(f"[{chat_id}] {text}")
        answer = call_llm(text)
        send_message(chat_id, answer)

        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        send_message(chat_id, "Ops... algo deu errado.")
        return "OK", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook_token():
    return telegram_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
