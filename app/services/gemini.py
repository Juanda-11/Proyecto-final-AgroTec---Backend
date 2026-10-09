"""Cliente mínimo de la API REST de Gemini. Devuelve None si no hay clave o falla (se usa el respaldo)."""
import asyncio
import json
import logging
from typing import Optional

import httpx

from app import config

log = logging.getLogger("agrotec.gemini")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = (
    "Eres AgroIA, asistente agronómico para pequeños agricultores de Nariño (Colombia). "
    "Responde en español sencillo, breve (máx. 120 palabras), con pasos prácticos. "
    "Considera clima andino, papa, café, hortalizas y fresa. No des dosis de agroquímicos; "
    "recomienda consultar al ICA/UMATA. Aclara que es orientación y no diagnóstico definitivo."
)


def available() -> bool:
    return bool(config.GEMINI_API_KEY)


async def generate(
    prompt: str,
    history: Optional[list[dict]] = None,
    image: Optional[tuple[str, str]] = None,
    json_schema: Optional[dict] = None,
    timeout: float = 25.0,
) -> Optional[str]:
    if not available():
        return None
    contents = []
    for m in history or []:
        contents.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]})
    parts: list[dict] = [{"text": prompt}]
    if image:
        parts.append({"inline_data": {"mime_type": image[1], "data": image[0]}})
    contents.append({"role": "user", "parts": parts})

    body: dict = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
    }
    if json_schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = json_schema
    models = [config.GEMINI_MODEL, *[m for m in config.GEMINI_FALLBACKS if m != config.GEMINI_MODEL]]
    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in models:
            for attempt in range(2):
                try:
                    r = await client.post(
                        URL.format(model=model), headers={"x-goog-api-key": config.GEMINI_API_KEY}, json=body
                    )
                    if r.status_code in (429, 500, 502, 503, 504):
                        log.warning("Gemini %s respondió %s (intento %s)", model, r.status_code, attempt + 1)
                        await asyncio.sleep(0.8 * (attempt + 1))
                        continue
                    r.raise_for_status()
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                    if text:
                        return text
                    break  # respuesta vacía/bloqueada: probar otro modelo
                except Exception as exc:  # red, 4xx, formato inesperado
                    log.warning("Gemini %s falló: %s", model, type(exc).__name__)
                    break
    return None


async def generate_json(prompt: str, schema: dict, **kw) -> Optional[dict]:
    text = await generate(prompt, json_schema=schema, **kw)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
