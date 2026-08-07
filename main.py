import os
import logging
import threading
import time
import requests
from flask import Flask, request

# Carrega variáveis
TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_URL = "https://hermes-agent-render-21ab.onrender.com/webhook"

# Modelos
LLM_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
FALLBACK_MODEL = "mistralai/mistral-7b-instruct:free"
IMAGE_MODEL = "stabilityai/sdxl-lightning"
VIDEO_MODEL = "Wendhe/Go_with_the_flow"

# Keepalive
def ping_server():
    while True:
        try:
            requests.get("https://hermes-agent-render-21ab.onrender.com/health")
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
        time.sleep(25 * 60)

threading.Thread(target=ping_server, daemon=True).start()

# Enviar mensagem
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# Enviar imagem
def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, files={"photo": photo_bytes}, data={"chat_id": chat_id})

# Enviar vídeo
def send_video(chat_id, video_bytes, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    requests.post(url, files={"video": video_bytes}, data={"chat_id": chat_id, "caption": caption})

# LLM via HuggingFace (com fallback)
def query_llm(chat_id, prompt):
    hf_url = f"https://api-inference.huggingface.co/models/{LLM_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    try:
        r = requests.post(hf_url, headers=headers, json={"inputs": prompt}, timeout=60)

        if r.status_code == 200:
            result = r.json()

            # ✅ Tratamento flexível para diferentes formatos
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                resposta = result[0]["generated_text"]
            elif isinstance(result, dict) and "generated_text" in result:
                resposta = result["generated_text"]
            elif isinstance(result, dict) and "text" in result:
                resposta = result["text"]
            else:
                resposta = str(result)[:500] if result else "Nenhuma resposta recebida."

            send_message(chat_id, resposta)
        else:
            logger.warning(f"HuggingFace failed ({r.status_code}): {r.text[:100]}")
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
        "model": FALLBACK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        resposta = r.json()["choices"][0]["message"]["content"]
        send_message(chat_id, f"[Fallback] {resposta}")
    except Exception as e:
        send_message(chat_id, f"❌ Erro: {str(e)}")

# Gerar imagem
def generate_image(chat_id, prompt):
    url = f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_photo(chat_id, r.content)
        else:
            send_message(chat_id, f"⚠️ Erro imagem: {r.status_code}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha gerar imagem: {str(e)}")

# Gerar vídeo
def generate_video(chat_id, prompt):
    url = f"https://api-inference.huggingface.co/models/{VIDEO_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {"inputs": prompt}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code == 200:
            send_video(chat_id, r.content, prompt)
        else:
            send_message(chat_id, f"⚠️ Erro vídeo: {r.status_code}")
    except Exception as e:
        send_message(chat_id, f"❌ Falha gerar vídeo: {str(e)}")

# Processar atualização
def process_update(update):
    try:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
        logger.info(f"[{chat_id}] {text}")

        if text.startswith("/img"):
            prompt_img = text[5:].strip() or "um gato fofo"
            generate_image(chat_id, prompt_img)
        elif text.startswith("/video"):
            prompt_video = text[7:].strip() or "um cachorro dançando"
            generate_video(chat_id, prompt_video)
        else:
            query_llm(chat_id, text)
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        send_message(chat_id, "❌ Ocorreu um erro interno.")

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

# Configurar webhook
def set_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    requests.post(url, json={"url": WEBHOOK_URL})

# Iniciar
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
