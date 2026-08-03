async def call_openrouter(prompt):
    import requests
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hermes-agent-render.onrender.com",
        "X-Title": "Hermes Agent"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Você é Hermes, um assistente útil e educado."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }
    try:
        logger.info(f"Enviando para OpenRouter: {payload}")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Resposta bruta: {response.text[:500]}")

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenRouter Error: {response.status_code} - {response.text}")
            return f"Erro na API: {response.status_code}"
    except Exception as e:
        logger.exception("Exceção ao chamar OpenRouter")
        return f"Exception: {e}"
