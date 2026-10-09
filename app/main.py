from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, schemas
from app.services import forecast as fc
from app.services import gemini, rules

app = FastAPI(title="AgroTec API", version="1.0.0",
              description="Servicios de IA para agricultura de precisión en Nariño")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "gemini": gemini.available(), "model": config.GEMINI_MODEL}


def _reading_text(r: schemas.Reading) -> str:
    return (f"humedad suelo {r.soil_moisture:.0f}%, temperatura {r.temperature:.1f}°C, "
            f"pH {r.ph:.1f}, UV {r.uv:.0f}, prob. lluvia {r.rain:.0f}%")


@app.post("/api/analyze", response_model=schemas.Assessment)
async def analyze(req: schemas.AnalyzeRequest):
    """Riesgo y riego: reglas deterministas + explicación en lenguaje natural con Gemini."""
    result = rules.assess(req.reading, req.crop)
    text = await gemini.generate(
        f"Cultivo: {req.crop}. Lecturas: {_reading_text(req.reading)}. "
        f"Alertas detectadas: {'; '.join(result.messages)}. "
        "Explica en 3 frases qué hacer hoy, priorizando lo más urgente."
    )
    if text:
        result.advice, result.source = text, "gemini"
    return result


@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(req: schemas.ChatRequest):
    ctx = ""
    if req.reading:
        ctx += f"Lecturas actuales de la finca: {_reading_text(req.reading)}. "
    if req.crop:
        ctx += f"Cultivo en foco: {req.crop}. "
    text = await gemini.generate(
        ctx + "Pregunta del agricultor: " + req.message,
        history=[m.model_dump() for m in req.history[-10:]],
    )
    if text:
        return schemas.ChatResponse(reply=text, source="gemini")
    return schemas.ChatResponse(reply=rules.keyword_reply(req.message), source="reglas")


DIAG_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "probable_causes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "recommendation": {"type": "STRING"},
        "urgency": {"type": "STRING", "enum": ["BAJO", "MEDIO", "ALTO"]},
    },
    "required": ["probable_causes", "recommendation", "urgency"],
}


@app.post("/api/diagnose", response_model=schemas.DiagnoseResponse)
async def diagnose(req: schemas.DiagnoseRequest):
    """Diagnóstico orientativo a partir de síntomas (y foto opcional, visión de Gemini)."""
    image = (req.image_base64, req.image_mime) if req.image_base64 else None
    data = await gemini.generate_json(
        f"Cultivo: {req.crop}. Síntomas descritos: {req.symptoms}. "
        "Lista hasta 3 causas probables (plaga, enfermedad o carencia), una recomendación "
        "práctica breve y la urgencia.",
        DIAG_SCHEMA, image=image,
    )
    if data and data.get("urgency") in ("BAJO", "MEDIO", "ALTO"):
        return schemas.DiagnoseResponse(
            probable_causes=[str(c) for c in data.get("probable_causes", [])][:3],
            recommendation=str(data.get("recommendation", "")),
            urgency=data["urgency"], disclaimer=rules.DISCLAIMER, source="gemini",
        )
    causes, rec, urgency = rules.rule_diagnosis(req.crop, req.symptoms)
    return schemas.DiagnoseResponse(
        probable_causes=causes, recommendation=rec, urgency=urgency,
        disclaimer=rules.DISCLAIMER, source="reglas",
    )


@app.post("/api/forecast", response_model=schemas.ForecastResponse)
def forecast(req: schemas.ForecastRequest):
    """Predicción de la tendencia de un sensor y tiempo estimado hasta el umbral crítico."""
    return fc.forecast(req.values, req.horizon, req.critical_below)


@app.post("/api/summary", response_model=schemas.SummaryResponse)
async def summary(req: schemas.SummaryRequest):
    """Resume la cola de alertas en un parte corto para el agricultor."""
    if not req.alerts:
        return schemas.SummaryResponse(summary="Sin alertas pendientes. Todo en orden.",
                                       priority="BAJO", source="reglas")
    joined = "; ".join(req.alerts[:20])
    priority = "ALTO" if any("ALTO" in a.upper() for a in req.alerts) else "MEDIO"
    text = await gemini.generate(
        f"Resume en máximo 3 frases estas alertas de la finca y di cuál atender primero: {joined}"
    )
    if text:
        return schemas.SummaryResponse(summary=text, priority=priority, source="gemini")
    return schemas.SummaryResponse(
        summary=f"{len(req.alerts)} alertas pendientes. Atienda primero: {req.alerts[0]}.",
        priority=priority, source="reglas",
    )
