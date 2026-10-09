from urllib.parse import parse_qsl, urlencode

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app import config, schemas
from app.services import forecast as fc
from app.services import gemini, rules

app = FastAPI(title="AgroTec API", version="1.0.0",
              description="Servicios de IA para agricultura de precisión en Nariño")

# Las rutas viven en un router que se monta con y sin el prefijo /api: así funcionan igual en local,
# con el rewrite de Vercel y cuando Vercel monta api/index.py bajo /api.
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@router.get("/health")
def health():
    return {"status": "ok", "gemini": gemini.available(), "model": config.GEMINI_MODEL}


def _reading_text(r: schemas.Reading) -> str:
    return (f"humedad suelo {r.soil_moisture:.0f}%, temperatura {r.temperature:.1f}°C, "
            f"pH {r.ph:.1f}, UV {r.uv:.0f}, prob. lluvia {r.rain:.0f}%")


@router.post("/analyze", response_model=schemas.Assessment)
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


@router.post("/chat", response_model=schemas.ChatResponse)
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


@router.post("/diagnose", response_model=schemas.DiagnoseResponse)
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


@router.post("/forecast", response_model=schemas.ForecastResponse)
def forecast(req: schemas.ForecastRequest):
    """Predicción de la tendencia de un sensor y tiempo estimado hasta el umbral crítico."""
    return fc.forecast(req.values, req.horizon, req.critical_below)


@router.post("/summary", response_model=schemas.SummaryResponse)
async def summary(req: schemas.SummaryRequest):
    """Resume la cola de alertas en un parte corto para el agricultor."""
    if not req.alerts:
        return schemas.SummaryResponse(summary="Sin alertas pendientes. Todo en orden.",
                                       priority="BAJO", source="reglas")
    joined = "; ".join(req.alerts[:20])
    priority = "ALTO" if any("ALTO" in a.upper() for a in req.alerts) else "MEDIO"
    text = await gemini.generate(
        "Resume en máximo 3 frases estas alertas de la finca y di cuál atender primero. "
        "Nota: ALTO/MEDIO indican el NIVEL DE RIESGO de cada sensor, no que el valor sea alto; "
        f"interpreta el valor numérico según el sensor. Alertas: {joined}"
    )
    if text:
        return schemas.SummaryResponse(summary=text, priority=priority, source="gemini")
    return schemas.SummaryResponse(
        summary=f"{len(req.alerts)} alertas pendientes. Atienda primero: {req.alerts[0]}.",
        priority=priority, source="reglas",
    )


app.include_router(router, prefix="/api")
app.include_router(router, include_in_schema=False)


@app.get("/", include_in_schema=False)
def root():
    return {"name": "AgroTec API", "docs": "/docs", "health": "/api/health"}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], include_in_schema=False)
def not_found(full_path: str, request: Request):
    """404 informativo: muestra la ruta que recibió la app (útil para depurar el despliegue)."""
    return JSONResponse({"detail": "Not Found", "path": request.url.path}, status_code=404)


class RestoreVercelPath:
    """Vercel reescribe /<ruta> a /api/index?__path=<ruta> (ver vercel.json) y la app solo ve /api/index.
    Este middleware ASGI vuelve a poner la ruta original antes de enrutar."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] in ("/api/index", "/index"):
            pairs = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            original = next((v for k, v in pairs if k == "__path"), None)
            if original is not None:
                path = "/" + original.lstrip("/")
                rest = urlencode([(k, v) for k, v in pairs if k != "__path"])
                scope = {**scope, "path": path, "raw_path": path.encode(), "query_string": rest.encode()}
        await self.inner(scope, receive, send)


# Debe ser el middleware más externo: se añade al final.
app.add_middleware(RestoreVercelPath)
