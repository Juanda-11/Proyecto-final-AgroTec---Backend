"""Cliente mínimo de la API REST de Gemini. Devuelve None si no hay clave o falla (se usa el respaldo)."""
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
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
    }
    if json_schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = json_schema
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                URL.format(model=config.GEMINI_MODEL),
                params={"key": config.GEMINI_API_KEY},
                json=body,
            )
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:  # red, cuota, bloqueo de seguridad, formato inesperado
        log.warning("Gemini no disponible: %s", type(exc).__name__)
        return None


async def generate_json(prompt: str, schema: dict, **kw) -> Optional[dict]:
    text = await generate(prompt, json_schema=schema, **kw)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
