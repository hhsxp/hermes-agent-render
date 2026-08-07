import os
import logging
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://hermes-agent-render.onrender.com/webhook"

# Modelos atualizados
LLM_MODEL = "nousresearch/tailwind-v1.5b"
IMAGE_MODEL = "stabilityai/sdxl-lightning"
VIDEO_MODEL = "Wendhe/Go_with_the_flow"

@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        logger.info(f"[{chat_id}] {text}")

        if text.startswith("/img "):
            prompt = text[5:]
            generate_image(chat_id, prompt)
        elif text.startswith("/video "):
            prompt = text[7:]
            generate_video(chat_id, prompt)
        else:
            query_llm(chat_id, text)

        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

def query_llm(chat_id, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent"
    }
    data = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200 and "choices" in r.json():
            resposta = r.json()["choices"][0]["message"]["content"]
            send_message(chat_id, resposta)
        else:
            send_message(chat_id, f"❌ Erro: {r.status_code} - {r.text[:100]}")
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
            send_message(chat_id, f"❌ Erro imagem: {r.status_code}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha imagem: {str(e)}")

def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/{VIDEO_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            send_message(chat_id, f"❌ Erro vídeo: {r.status_code}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha vídeo: {str(e)}")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, files={"photo": photo_bytes}, data={"chat_id": chat_id})

def send_video(chat_id, video_bytes, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    requests.post(url, files={"video": video_bytes}, data={"chat_id": chat_id, "caption": caption})

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    requests.post(url, json={"url": WEBHOOK_URL})
