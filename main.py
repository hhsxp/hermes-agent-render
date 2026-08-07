import os
import logging
import threading
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App Flask
app = Flask(__name__)

# Webhook URL
WEBHOOK_URL = "https://hermes-agent-render-21ab.onrender.com/webhook"

# Modelos
LLM_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"

# Keepalive
def ping_server():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com/health")
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
        time.sleep(25 * 60)

threading.Thread(target=ping_server, daemon=True).start()

# Funções auxiliares
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, files={"photo": photo_bytes}, data={"chat_id": chat_id})

def send_video(chat_id, video_bytes, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    requests.post(url, files={"video": video_bytes}, data={"chat_id": chat_id, "caption": caption})

# Processamento de mensagens
def process_update(update):
    try:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
        logger.info(f"[{chat_id}] {text}")

        # Comandos específicos
        if text.startswith("/start") or text.startswith("/help"):
            send_message(chat_id, "🤖 Hermes Agent Online!\nComandos:\n/img <descrição> - Gera imagem\n/video <descrição> - Gera vídeo")
        elif text.startswith("/img"):
            parts = text.split(" ", 1)
            prompt_img = parts[1] if len(parts) > 1 else "um gato fofo"
            generate_image(chat_id, prompt_img)
        elif text.startswith("/video"):
            parts = text.split(" ", 1)
            prompt_video = parts[1] if len(parts) > 1 else "um cachorro dançando"
            generate_video(chat_id, prompt_video)
        else:
            query_llm(chat_id, text)
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        send_message(chat_id, "❌ Ocorreu um erro interno.")

# LLM via HuggingFace
def query_llm(chat_id, prompt):
    hf_url = f"https://api-inference.huggingface.com/models/{LLM_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    try:
        r = requests.post(hf_url, headers=headers, json={"inputs": prompt}, timeout=60)
        if r.status_code == 200:
            result = r.json()
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                send_message(chat_id, result[0]["generated_text"])
            elif isinstance(result, dict) and "text" in result:
                send_message(chat_id, result["text"])
            else:
                send_message(chat_id, f"Resposta inesperada: {str(result)[:200]}")
        else:
            logger.warning(f"HF falhou ({r.status_code})")
            fallback_llm(chat_id, prompt)
    except Exception as e:
        logger.error(f"Erro no HuggingFace: {e}")
        fallback_llm(chat_id, prompt)

# Fallback via OpenRouter
def fallback_llm(chat_id, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render-21ab.onrender.com",
        "X-Title": "Hermes Agent"
    }
    data = {
        "model": "meta-llama/llama-4-maverick",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        resposta = r.json()["choices"][0]["message"]["content"]
        send_message(chat_id, f"[Resposta alternativa] {resposta}")
    except Exception as e:
        send_message(chat_id, f"❌ Erro crítico: {str(e)}")

# Geração de imagem
def generate_image(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/stabilityai/sdxl-lightning"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_photo(chat_id, r.content)
        else:
            send_message(chat_id, f"⚠️ Erro imagem ({r.status_code})")
    except Exception as e:
        send_message(chat_id, f"❌ Falha gerar imagem: {str(e)}")

# Geração de vídeo
def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.com/models/Wendhe/Go_with_the_flow"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            send_message(chat_id, f"⚠️ Erro vídeo ({r.status_code})")
    except Exception as e:
        send_message(chat_id, f"❌ Falha gerar vídeo: {str(e)}")

# Rotas Flask
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

# Configura webhook
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    requests.post(url, json={"url": WEBHOOK_URL})

# Início
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
