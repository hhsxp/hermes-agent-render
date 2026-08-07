import os
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WEBHOOK_URL = "https://hermes-agent-render-21ab.onrender.com/webhook"

LLM_MODEL = "meta-llama/llama-4-maverick"
IMAGE_MODEL = "stabilityai/sdxl-lightning"
VIDEO_MODEL = "Wendhe/Go_with_the_flow"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, files={"photo": photo_bytes}, data={"chat_id": chat_id})

def send_video(chat_id, video_bytes, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    requests.post(url, files={"video": video_bytes}, data={"chat_id": chat_id, "caption": caption})

def query_llm(chat_id, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render-21ab.onrender.com",
        "X-Title": "Hermes Agent"
    }
    data = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200:
            resposta = r.json()["choices"][0]["message"]["content"]
            send_message(chat_id, resposta)
        else:
            msg_error = r.text[:100] if r.text else "Erro desconhecido"
            send_message(chat_id, f"❌ Erro ({r.status_code}): {msg_error}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha: {str(e)}")

def generate_image(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/{IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            send_photo(chat_id, r.content)
        else:
            logger.warning(f"Image failed: {r.text}")
            query_llm(chat_id, f"Desenhe digitalmente: {prompt}")
    except Exception:
        query_llm(chat_id, f"Desenhe digitalmente: {prompt}")

def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/{VIDEO_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            logger.warning(f"Video failed: {r.text}")
            query_llm(chat_id, prompt)
    except Exception:
        query_llm(chat_id, prompt)

def process_update(update):
    try:
        chat_id = update["message"]["chat"]["id"]
        message = update["message"]
        text = message.get("text", "").strip()
        logger.info(f"[{chat_id}] {text}")

        if text.startswith("/img"):
            prompt_img = text.split(" ", 1)[1] if len(text.split(" ")) > 1 else "um gato fofo"
            generate_image(chat_id, prompt_img)
        elif text.startswith("/video"):
            prompt_video = text.split(" ", 1)[1] if len(text.split(" ")) > 1 else "um gato dançando"
            generate_video(chat_id, prompt_video)
        else:
            query_llm(chat_id, text)
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")

@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        process_update(request.get_json())
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    requests.post(url, json={"url": WEBHOOK_URL})

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
