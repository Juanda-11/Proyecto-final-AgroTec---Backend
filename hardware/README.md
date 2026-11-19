# AgroTec — Nodo sensor (ESP32)

Nodo físico que mide la maqueta y envía las lecturas por WiFi al backend. La app las muestra en tiempo real
(interruptor **Simulado / Sensor real** en la pantalla Inicio).

```
Sensores ──► ESP32 ──HTTPS POST──► API (FastAPI en Vercel) ──► Upstash Redis ◄── App (consulta cada 8 s)
```

## Componentes
| Componente | Magnitud | Pin (ESP32) |
|---|---|---|
| DHT22 | Temperatura y humedad del aire | GPIO 32 (digital) |
| Sensor de humedad de suelo capacitivo | Humedad del suelo | GPIO 34 (ADC1) |
| Módulo Water Sensor (analógico) | Lluvia / agua | GPIO 35 (ADC1) |
| Sensor UV analógico (opcional) | Radiación UV | GPIO 33 (ADC1) |

- Todos los sensores se alimentan a 3.3 V. Las entradas analógicas usan pines ADC1 (32–39), porque el ADC2 no funciona con el WiFi activo.
- El pH y el UV no se miden en esta versión: la app los simula y los marca como **SIM**; los medidos por el nodo aparecen como **REAL**.

## Firmware (`firmware/agrotec_node`)
- Lee los sensores, promedia 16 muestras analógicas (ADC de 12 bits) y las convierte a porcentaje con valores de calibración.
- Envía un JSON por HTTPS cada 10 s a `POST /api/readings`, con la clave del dispositivo en la cabecera `X-Device-Key`.
- Configuración: copiar `config.example.h` como `config.h` (ignorado por git) y completar WiFi, `API_URL`, `DEVICE_KEY` y la calibración.
- `CALIBRATION_MODE 1` imprime los valores crudos por el Monitor Serie (115200) sin enviar nada.
- `firmware/sensor_test`: sketch independiente que lee los sensores sin WiFi, útil para probar el cableado.
- `firmware/agrotec_node/test`: pruebas en PC de las conversiones (`conversions.h`).

### Calibración
| Valor | Cómo medirlo |
|---|---|
| `SOIL_RAW_DRY` | Sensor de suelo al aire |
| `SOIL_RAW_WET` | Sensor de suelo sumergido en agua hasta la línea |
| `RAIN_RAW_DRY` | Sensor de lluvia seco |
| `RAIN_RAW_WET` | Sensor de lluvia con gotas sobre las pistas |

El *Water Sensor* marca cerca de 0 en seco y sube al mojarse (el FC-37 hace lo contrario); la fórmula de conversión funciona con ambos.

## API de ingesta
| Endpoint | Función |
|---|---|
| `POST /api/readings` | Recibe una lectura del nodo (clave en `X-Device-Key`, validada con Pydantic) |
| `GET /api/readings/latest` | Última lectura y si el nodo está en línea (reportó en los últimos 30 s) |
| `GET /api/readings/history` | Historial reciente |

Variables de entorno del backend: `DEVICE_API_KEY` y el almacenamiento Upstash Redis (`KV_REST_API_URL`/`KV_REST_API_TOKEN`
o `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN`). Sin Redis las lecturas se guardan solo en memoria, lo que no es fiable en Vercel (sin estado).

`tools/simulate_device.py` envía lecturas de prueba a la API como si fuera el nodo, útil para verificar la cadena completa sin la placa:
```bash
python hardware/tools/simulate_device.py --url https://TU-BACKEND.vercel.app --key TU_DEVICE_API_KEY
```

## Limitaciones conocidas
- El firmware usa `client.setInsecure()` (no valida el certificado del servidor) para simplificar la demostración; en producción habría que fijar el certificado raíz.
- El ESP32 solo se conecta a redes WiFi de 2.4 GHz y no admite portales cautivos ni WPA2-Enterprise.
- Los planes gratuitos de Vercel y Upstash tienen cuotas; con envíos cada 10 s sobran para una demostración.
