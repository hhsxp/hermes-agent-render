import os
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App Flask
app = Flask(__name__)

def call_llm(prompt, image_url=None):
    api_url = "https://api-inference.huggingface.com/models/Qwen/Qwen2.5-VL-7B-Instruct"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    if image_url:
        payload = {"image_url": image_url, "prompt": prompt}
    else:
        payload = {"inputs": prompt}

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "Erro: resposta vazia.")
            elif isinstance(result, dict) and "error" in result:
                return f"Erro na API: {result['error']}"
            else:
                return str(result)
        else:
            return f"Erro HTTP {response.status_code}: {response.text[:100]}"
    except Exception as e:
        logger.error(f"Falha na API: {str(e)}")
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
