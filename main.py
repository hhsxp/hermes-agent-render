import os
import logging
import threading
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv

# --- Carrega variáveis ---
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- Flask ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configurações ---
WEBHOOK_URL = "https://hermes-agent-render-21ab.onrender.com/webhook"

# Modelos atualizados
LLM_MODEL = "meta-llama/llama-4-maverick"
IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1024-v12"
VIDEO_MODEL = "Wendhe/Go_with_the_flow"

# --- Keepalive ---
def keepalive():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com")
        except Exception as e:
            logger.warning(f"Ping falhou: {str(e)}")
        time.sleep(25 * 60)

threading.Thread(target=keepalive, daemon=True).start()

# --- Funções auxiliares ---
def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def send_photo(chat_id, photo_bytes):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        files={"photo": photo_bytes},
        data={"chat_id": chat_id}
    )

def send_video(chat_id, video_bytes, caption=""):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendVideo",
        files={"video": video_bytes},
        data={"chat_id": chat_id, "caption": caption}
    )

# --- LLM via OpenRouter ---
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
        "max_tokens": 2048,
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200:
            resposta = r.json()["choices"][0]["message"]["content"]
            send_message(chat_id, resposta)
        else:
            err = r.json().get("error", {}).get("message", "Erro desconhecido")
            send_message(chat_id, f"⚠️ Erro: {err[:200]}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha: {str(e)}")

# --- Gerar imagem (HuggingFace) ---
def generate_image(chat_id, prompt):
    url = f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_photo(chat_id, r.content)
        else:
            logger.warning(f"Fallback imagem: {r.status_code}")
            query_llm(chat_id, f"Desenhe digitalmente: {prompt}")
    except Exception:
        query_llm(chat_id, f"Desenhe digitalmente: {prompt}")

# --- Gerar vídeo (HuggingFace) ---
def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.co/models/{VIDEO_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            logger.warning(f"Fallback vídeo: {r.status_code}")
            query_llm(chat_id, prompt)
    except Exception:
        query_llm(chat_id, prompt)

# --- Processamento de atualizações ---
def process_update(update):
    try:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
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
        send_message(chat_id, "❌ Ocorreu um erro no processamento.")

# --- Rotas Flask ---
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
        logger.error(f"Erro no webhook: {str(e)}")
        return "OK", 200

# --- Configura webhook ---
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    r = requests.post(url, json={"url": WEBHOOK_URL})
    if r.status_code == 200:
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
    else:
        logger.warning(f"❌ Erro no webhook: {r.text}")

# --- Inicializa ---
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
