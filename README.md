# AgroTec — Backend (Python / FastAPI)

API de IA para la app móvil AgroTec (agricultura de precisión en Nariño).
Proyecto final de Estructuras de Datos — Universidad Cooperativa de Colombia, Campus Pasto.

## Funcionalidades de IA

| Endpoint | Qué hace | Técnica |
|---|---|---|
| `POST /api/chat` | Asistente agrónomo conversacional con contexto de sensores | Gemini + respaldo por reglas |
| `POST /api/analyze` | Riesgo, riego y consejo del día por cultivo | Reglas por cultivo + explicación Gemini |
| `POST /api/diagnose` | Diagnóstico orientativo por síntomas y **foto** | Gemini multimodal (JSON estructurado) + reglas |
| `POST /api/forecast` | Predicción de tendencia y horas hasta nivel crítico | Regresión lineal (mínimos cuadrados) |
| `POST /api/summary` | Parte resumido de la cola de alertas | Gemini + respaldo |
| `GET /api/health` | Estado y si Gemini está activo | — |

Sin `GEMINI_API_KEY` todo funciona con el respaldo de reglas (campo `source: "reglas"`).

## Ejecutar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # y pega tu GEMINI_API_KEY
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
pytest
```
Docs interactivas: http://localhost:8000/docs

## Despliegue en Vercel
Importa este repo en Vercel (framework: Other). `api/index.py` + `vercel.json` ya están listos.
Define las variables `GEMINI_API_KEY`, `GEMINI_MODEL` y `CORS_ORIGINS` (URL del frontend) en *Settings → Environment Variables*.
