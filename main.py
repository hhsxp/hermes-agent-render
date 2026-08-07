import os
import logging
import threading
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv

# --- Configurações ---
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")  # Chave HuggingFace para imagens
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Opcional: Whisper via Groq

# --- App Flask ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Webhook URL dinâmico ---
WEBHOOK_URL = f"https://hermes-agent-render.onrender.com/{TOKEN}"

# --- Modelos atualizados ---
LLM_MODEL = "meta-llama/llama-4-maverick"  # Grátis no OpenRouter
IMAGE_MODEL = "stabilityai/sdxl-lightning"  # Mais rápido que SDXL
VIDEO_MODEL = "Wendhe/Go_with_the_flow"  # Geração de vídeo

# --- Rotas Flask ---
@app.route("/")
def index():
    return "🤖 Hermes Agent Online!", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route(f"/{TOKEN}", methods=["GET", "POST"])
def telegram_webhook():
    if request.method == "POST":
        process_update(request.get_json())
        return "OK", 200
    return "✅ Webhook configurado!", 200

@app.route("/webhook", methods=["POST"])
def webhook_route():
    process_update(request.get_json())
    return "OK", 200

# --- Processa atualizações do Telegram ---
def process_update(update):
    try:
        chat_id = update["message"]["chat"]["id"]
        message = update["message"]

        if "text" in message:
            text = message["text"].strip()
            logger.info(f"[MSG] {chat_id}: {text}")

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

# --- LLM via OpenRouter ---
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
        if r.status_code == 200:
            resposta = r.json()
            if "choices" in resposta:
                send_message(chat_id, resposta["choices"][0]["message"]["content"])
            else:
                send_message(chat_id, f"⚠️ Resposta inesperada: {resposta}")
        else:
            send_message(chat_id, f"❌ Erro na API: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha na conexão: {str(e)}")

# --- Geração de Imagens (HuggingFace) ---
def generate_image(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/{IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}

    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            send_photo(chat_id, r.content)
        else:
            send_message(chat_id, f"❌ Erro ao gerar imagem: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha ao gerar imagem: {str(e)}")

# --- Geração de Vídeo (HuggingFace) ---
def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/{VIDEO_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}

    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            send_message(chat_id, f"❌ Erro ao gerar vídeo: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha ao gerar vídeo: {str(e)}")

# --- Mensagens do Telegram ---
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    files = {"photo": photo_bytes}
    requests.post(url, files=files, data={"chat_id": chat_id})

def send_video(chat_id, video_bytes, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    files = {"video": video_bytes}
    requests.post(url, files=files, data={"chat_id": chat_id, "caption": caption})

# --- Configura webhook ---
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    r = requests.post(url, json={"url": WEBHOOK_URL})
    if r.status_code == 200:
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
    else:
        logger.warning(f"⚠️ Erro ao configurar webhook: {r.text}")

# --- Start ---
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
