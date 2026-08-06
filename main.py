import os
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}.onrender.com")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Groq API endpoint (OpenRouter fallback)
def call_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "poolside/laguna-s-2.1:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Erro na API: {r.status_code} - {r.text[:100]}"
    except Exception as e:
        return f"Falha na conexão: {str(e)}"

# Telegram webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        answer = call_openrouter(text)

        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(send_url, json={"chat_id": chat_id, "text": answer})

        logger.info(f"[{chat_id}] {text} -> {answer}")
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

# Root route for health check
@app.route("/")
def index():
    return "🤖 Hermes Bot Online!", 200

# Set webhook on startup
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    full_url = f"{WEBHOOK_URL}/{TOKEN}"
    requests.post(url, json={"url": full_url, "allowed_updates": ["message"]})

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
