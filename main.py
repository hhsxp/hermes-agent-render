import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Servidor web leve só pra Render saber que tá vivo ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Hermes Agent Online!")

def start_webserver():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Começa o servidor web em outra thread
t = threading.Thread(target=start_webserver)
t.daemon = True
t.start()

# Agora começa o Hermes Agent (aqui você adiciona a lógica real depois)
print("Iniciando Hermes Agent...")
# TODO: Integrar com Telegram / OpenRouter depois

# Mantém o processo vivo
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("Encerrando...")
