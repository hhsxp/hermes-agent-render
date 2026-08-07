import os
import logging
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

# Configurações
TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")  # Token do HuggingFace
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# --- HuggingFace Multimodal (Qwen2.5-VL) ---
def query_huggingface(prompt, image_url=None):
    api_url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-VL-7B-Instruct"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    if image_url:
        payload = {"image_url": image_url, "prompt": prompt}
    else:
        payload = {"inputs": prompt}

    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            result = response.json()
            return result[0]['generated_text'] if isinstance(result, list) else str(result)
        else:
            return "Resposta recebida."
    else:
        return f"Erro HF: {response.status_code}"

# --- Text-to-Image (Stable Diffusion XL) ---
def generate_image(prompt):
    api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1024-v12"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}

    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.content  # Imagem em bytes
    else:
        return None

# --- Mensagem para Telegram ---
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo_bytes, caption=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    files = {"photo": photo_bytes}
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    requests.post(url, files=files, data=data)

# --- Rotas Flask ---
@app.route('/')
def index():
    return "Bot Online!", 200

@app.route('/' + TOKEN, methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        chat_id = update['message']['chat']['id']
        message_text = update['message']['text']

        logger.info(f"[{chat_id}] {message_text}")

        # Comando especial: gerar imagem
        if message_text.startswith('/img'):
            prompt = message_text[4:].strip()
            if not prompt:
                send_message(chat_id, "Envie um prompt após /img. Exemplo:\n`/img um gato azul`", parse_mode="Markdown")
                return "OK", 200

            image_data = generate_image(prompt)
            if image_data:
                send_photo(chat_id, image_data, caption=f"🖼️ Prompt: {prompt}")
            else:
                send_message(chat_id, "Falha ao gerar imagem.")

        # Responder normalmente com IA multimodal
        else:
            # Opcional: detectar foto
            if 'photo' in update['message']:
                file_id = update['message']['photo'][-1]['file_id']
                file_url = get_telegram_file_url(file_id)
                answer = query_huggingface("O que está escrito nessa imagem?", image_url=file_url)
                send_message(chat_id, answer)
            else:
                answer = query_huggingface(message_text)
                send_message(chat_id, answer)

        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        send_message(chat_id, "Ops... algo deu errado.")
        return "OK", 200

def get_telegram_file_url(file_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile"
    response = requests.post(url, json={"file_id": file_id}).json()
    file_path = response['result']['file_path']
    return f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

# --- Iniciar serviço ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
