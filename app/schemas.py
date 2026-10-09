from typing import Literal, Optional

from pydantic import BaseModel, Field

Risk = Literal["BAJO", "MEDIO", "ALTO"]


class Reading(BaseModel):
    """Una lectura completa de los sensores simulados."""

    soil_moisture: float = Field(ge=0, le=100, description="Humedad del suelo (%)")
    temperature: float = Field(ge=-10, le=60, description="Temperatura (°C)")
    ph: float = Field(ge=0, le=14)
    uv: float = Field(default=0, ge=0, le=100, description="Índice UV simulado (0-100)")
    rain: float = Field(default=0, ge=0, le=100, description="Probabilidad de lluvia (%)")
    timestamp: Optional[int] = None


class AnalyzeRequest(BaseModel):
    reading: Reading
    crop: str = "papa"


class Assessment(BaseModel):
    risk: Risk
    score: int
    irrigation: Literal["NINGUNO", "RECOMENDADO", "URGENTE"]
    messages: list[str]
    advice: str
    source: Literal["gemini", "reglas"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    reading: Optional[Reading] = None
    crop: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    source: Literal["gemini", "reglas"]


class DiagnoseRequest(BaseModel):
    crop: str = "papa"
    symptoms: str = Field(min_length=3, max_length=1500)
    image_base64: Optional[str] = Field(default=None, max_length=4_000_000)
    image_mime: str = "image/jpeg"


class DiagnoseResponse(BaseModel):
    probable_causes: list[str]
    recommendation: str
    urgency: Risk
    disclaimer: str
    source: Literal["gemini", "reglas"]


class ForecastRequest(BaseModel):
    values: list[float] = Field(min_length=3, max_length=500, description="Serie histórica, más antigua primero")
    horizon: int = Field(default=6, ge=1, le=48)
    critical_below: Optional[float] = Field(default=30, description="Umbral crítico inferior")


class ForecastResponse(BaseModel):
    forecast: list[float]
    slope: float
    r2: float
    hours_to_critical: Optional[float]
    trend: Literal["SUBE", "BAJA", "ESTABLE"]


class SummaryRequest(BaseModel):
    alerts: list[str] = Field(max_length=50)


class SummaryResponse(BaseModel):
    summary: str
    priority: Risk
    source: Literal["gemini", "reglas"]
