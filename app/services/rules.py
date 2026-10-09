"""Motor de reglas transparente. También sirve de respaldo cuando Gemini no está disponible."""
from app.schemas import Assessment, Reading, Risk

DISCLAIMER = (
    "Orientación de apoyo para un prototipo académico; no reemplaza la visita de un "
    "agrónomo o de la UMATA/ICA de su municipio."
)

# Rangos de referencia por cultivo típico de Nariño: (humedad_min, ph_min, ph_max, temp_max)
CROP_RANGES = {
    "papa": (40, 5.0, 6.5, 24),
    "cafe": (45, 5.0, 6.5, 28),
    "café": (45, 5.0, 6.5, 28),
    "hortalizas": (50, 6.0, 7.0, 26),
    "maiz": (40, 5.8, 7.0, 30),
    "maíz": (40, 5.8, 7.0, 30),
    "fresa": (55, 5.5, 6.5, 25),
}
DEFAULT_RANGE = (40, 5.4, 7.4, 28)


def crop_range(crop: str):
    return CROP_RANGES.get(crop.strip().lower(), DEFAULT_RANGE)


def level(score: int) -> Risk:
    return "ALTO" if score >= 5 else "MEDIO" if score >= 2 else "BAJO"


def assess(reading: Reading, crop: str = "papa") -> Assessment:
    moist_min, ph_min, ph_max, temp_max = crop_range(crop)
    score = 0
    messages: list[str] = []

    if reading.soil_moisture < moist_min - 15:
        score += 3
        messages.append(f"Humedad crítica ({reading.soil_moisture:.0f}%): riesgo de estrés hídrico.")
    elif reading.soil_moisture < moist_min:
        score += 1
        messages.append(f"Humedad por debajo del objetivo para {crop} ({moist_min}%).")
    if reading.temperature > temp_max:
        score += 2
        messages.append(f"Temperatura alta ({reading.temperature:.1f} °C) para {crop}.")
    if reading.ph < ph_min or reading.ph > ph_max:
        score += 2
        messages.append(f"pH {reading.ph:.1f} fuera del rango {ph_min}-{ph_max}.")
    if reading.rain > 70:
        score += 1
        messages.append("Alta probabilidad de lluvia: vigile encharcamiento y hongos.")
    if reading.uv > 80:
        score += 1
        messages.append("Radiación UV muy alta: proteja plántulas y cultivos bajo invernadero.")

    if reading.soil_moisture < moist_min - 20:
        irrigation = "URGENTE"
    elif reading.soil_moisture < moist_min and reading.rain < 40:
        irrigation = "RECOMENDADO"
    else:
        irrigation = "NINGUNO"

    if not messages:
        messages.append("Condiciones dentro de los rangos esperados.")

    advice = {
        "URGENTE": "Riegue hoy en las horas frescas (temprano o al atardecer) y revise de nuevo en 2 horas.",
        "RECOMENDADO": "Programe un riego ligero; evite regar si se espera lluvia en las próximas horas.",
        "NINGUNO": "No es necesario regar. Mantenga el monitoreo.",
    }[irrigation]

    return Assessment(
        risk=level(score), score=score, irrigation=irrigation,
        messages=messages, advice=advice, source="reglas",
    )


KEYWORD_REPLIES = [
    (("humedad", "riego", "regar"),
     "Si la humedad del suelo baja del objetivo de su cultivo, programe riego en horas frescas. "
     "Con lluvia probable, espere antes de regar."),
    (("plaga", "mosca", "ácaro", "acaro", "gusano"),
     "Para plagas, inspeccione el envés de las hojas, aísle plantas afectadas y consulte al ICA/UMATA "
     "antes de aplicar productos."),
    (("ph", "ácido", "acido", "cal"),
     "Un pH fuera de rango limita la absorción de nutrientes. Un análisis de suelo indica si necesita "
     "encalar (suelo ácido) o corregir (suelo alcalino)."),
    (("fertiliz", "abono", "nutrient"),
     "La fertilización depende del cultivo, la etapa y el análisis de suelo. Evite aplicar antes de lluvias fuertes."),
    (("tizón", "tizon", "gota", "roya", "hongo"),
     "Hongos como tizón tardío o roya prosperan con humedad alta y temperaturas frescas. "
     "Mejore ventilación, retire hojas afectadas y consulte por fungicidas autorizados."),
]


def keyword_reply(message: str) -> str:
    low = message.lower()
    for keys, reply in KEYWORD_REPLIES:
        if any(k in low for k in keys):
            return reply
    return ("Puedo ayudarte con riego, plagas, enfermedades, pH y fertilización. "
            "Cuéntame el cultivo y qué observas.")


SYMPTOM_RULES = [
    (("amarill", "clorosis"), "Deficiencia de nitrógeno o exceso de agua", "MEDIO"),
    (("mancha", "tizón", "tizon", "negr"), "Hongo foliar (p. ej. tizón tardío)", "ALTO"),
    (("enroll",), "Estrés hídrico, ácaros o virus", "MEDIO"),
    (("mosca blanca", "polvillo", "insecto"), "Plaga chupadora (mosca blanca, pulgón)", "MEDIO"),
    (("podr", "pudri", "raíz", "raiz", "marchit"), "Pudrición radicular por exceso de humedad", "ALTO"),
    (("roya", "naranja"), "Roya", "ALTO"),
]


def rule_diagnosis(crop: str, symptoms: str):
    low = symptoms.lower()
    causes, urgency_rank = [], 0
    rank = {"BAJO": 0, "MEDIO": 1, "ALTO": 2}
    for keys, cause, urg in SYMPTOM_RULES:
        if any(k in low for k in keys):
            causes.append(cause)
            urgency_rank = max(urgency_rank, rank[urg])
    if not causes:
        causes = ["Síntomas inespecíficos: se requiere inspección en campo"]
    urgency: Risk = ["BAJO", "MEDIO", "ALTO"][urgency_rank]  # type: ignore[assignment]
    rec = (f"Para {crop}: aísle la zona afectada, evite regar sobre el follaje, tome fotos del avance y "
           "solicite visita técnica antes de aplicar agroquímicos.")
    return causes, rec, urgency
