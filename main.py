import os
import requests
from flask import Flask, request, jsonify, Response
import logging

# Variáveis de ambiente
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")  # Novo: para gerar imagens
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Novo: para STT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# ========================
# 📝 Função Qwen via OpenRouter (principal)
# ========================
def call_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://hermes-agent-render-21ab.onrender.com",
        "X-Title": "Hermes Agent",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen-2.5-72b-instruct",
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente inteligente."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Erro ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        return f"Falha na API: {str(e)}"

# ========================
# 🖼️ Gerar Imagem via HuggingFace
# ========================
def generate_image(prompt):
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1024-v12",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": prompt}
        )
        if r.status_code == 200:
            return r.content
        else:
            return None
    except:
        return None

# ========================
# 🎤 Converter Áudio para Texto (Whisper via Groq)
# ========================
def transcribe_audio(file_path):
    try:
        files = {"file": (os.path.basename(file_path), open(file_path, 'rb'), 'audio/mpeg')}
        data = {"model": "whisper-large-v3"}
        r = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files=files,
            data=data
        )
        if r.status_code == 200:
            return r.json().get("text", "")
        else:
            return "Erro ao transcrever áudio."
    except Exception as e:
        return f"Falha: {str(e)}"

# ========================
# 🎬 Tentar gerar vídeo via Space pública (limitado)
# ========================
def generate_video(prompt):
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/spaces/PixArt/PixArt-alpha/",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": prompt}
        )
        if r.status_code == 200:
            return r.json().get("video_url", "")
        else:
            return "Erro ao gerar vídeo."
    except:
        return "Falha ao gerar vídeo."

# ========================
# ✅ Rotas Flask
# ========================

@app.route("/")
def index():
    return "🤖 Hermes Bot Online!", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json()

        # Comandos de texto
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"]["text"].strip()

            # Comando: /img <descrição>
            if text.startswith("/img "):
                prompt = text[5:]
                img_bytes = generate_image(prompt)
                if img_bytes:
                    url = "https://api.telegram.org/bot" + TOKEN + "/sendPhoto"
                    requests.post(url, files={"photo": img_bytes}, data={"chat_id": chat_id})
                else:
                    send_message(chat_id, "Falha ao gerar imagem.")
                return "OK", 200

            # Comando: /video <descrição>
            elif text.startswith("/video "):
                prompt = text[7:]
                result = generate_video(prompt)
                send_message(chat_id, result)
                return "OK", 200

            # Mensagem normal (responde com Qwen)
            else:
                answer = call_openrouter(text)
                send_message(chat_id, answer)
                return "OK", 200

        # Recepção de áudio (voice note)
        elif "message" in update and "voice" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            file_id = update["message"]["voice"]["file_id"]
            file_path = download_telegram_file(file_id)
            if file_path:
                transcript = transcribe_audio(file_path)
                send_message(chat_id, f"📝 Transcrição: {transcript}")
            else:
                send_message(chat_id, "Não foi possível baixar áudio.")
            return "OK", 200

        return "OK", 200

    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "OK", 200

# ========================
# 🛰️ Funções auxiliares
# ========================

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def download_telegram_file(file_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getFile"
    resp = requests.post(url, json={"file_id": file_id})
    if resp.status_code == 200:
        path = resp.json()["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{path}"
        local_file = "temp_audio.mp3"
        r = requests.get(download_url)
        if r.status_code == 200:
            with open(local_file, "wb") as f:
                f.write(r.content)
            return local_file
    return None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
