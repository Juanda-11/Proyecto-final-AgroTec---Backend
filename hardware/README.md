# AgroTec — Maqueta de hardware (nodo sensor ESP32)

Nodo sensor real que mide la maqueta y envía los datos por WiFi al backend; la app los muestra en tiempo real
(interruptor **Simulado / Sensor real** en la pantalla Inicio).

```
Sensores ──► ESP32 ──WiFi/HTTPS POST──► API (Vercel) ──► Upstash Redis ◄── App (consulta cada ~8 s)
```

> **¿Primera vez armando un circuito?** Sigan la guía paso a paso: [`GUIA_ARMADO.md`](GUIA_ARMADO.md).

## 1. Lista de compra (precios estimados en COP; verifíquenlos, varían por tienda)
| # | Componente | Cant. | Estimado | Nota |
|---|---|---|---|---|
| 1 | **ESP32 DevKit V1** (ESP-WROOM-32, 30 pines) con cable micro-USB **de datos** | 1 (ideal 2) | 30.000–45.000 c/u | El 2.º es repuesto: si se quema, la entrega no se cae |
| 2 | **Sensor de humedad de suelo capacitivo v1.2** | 2 | 8.000–15.000 c/u | No compren el de 2 puntas "resistivo": se corroe en días |
| 3 | **DHT22 (AM2302)** en módulo con 3 pines | 1 | 15.000–30.000 | Temperatura y humedad del aire (el DHT11 también sirve, pero es peor) |
| 4 | **Módulo sensor de lluvia FC-37 / YL-83** (placa + comparador, con salida AO) | 1 | 5.000–10.000 | |
| 5 | **Sensor UV** (opcional): GUVA-S12SD, **UVM-30A** o **ML8511/GY-8511** (los tres sirven; si no consiguen ninguno, se omite) | 0–1 | 15.000–30.000 | Se elige con `UV_SENSOR` en `config.h` (ver `GUIA_ARMADO.md` §4.5) |
| 6 | **Protoboard 830 puntos** + **cables dupont** (M-M, M-H, H-H) | 1 kit | 15.000–25.000 | |
| 7 | Cargador USB 5 V / 1 A (sirve el de un celular) o **power bank** | 1 | 0–25.000 | El power bank permite demostrar sin enchufe |
| 8 | Materiales de la maqueta: base de madera/acrílico, matera con tierra y planta, caja plástica para el ESP32, silicona caliente | — | 30.000–60.000 | |
| | **Total esencial** | | **≈ 130.000–250.000** | |

**Opcionales:**
- **Sensor de pH analógico (PH-4502C + electrodo)**, 60.000–120.000, **más soluciones buffer pH 4 y 7** para calibrarlo. Es lo menos fiable de la lista:
  si no hay tiempo, dejen el pH simulado (la app lo indica) y expliquen por qué en la sustentación.
- **Relé 5 V (1 canal) + mini bomba de agua + manguera** (~30.000–45.000) para mostrar riego automático. El firmware actual solo *envía* datos;
  recibir órdenes desde la app sería una ampliación.

**Dónde comprar:** tiendas de electrónica con envío a Pasto (Mercado Libre Colombia, Didácticas Electrónicas, Sigma Electrónica, Electronilab, etc.) o locales en Pasto.
Pidan **hoy**: el envío tarda 2–5 días y queda una semana.

## 2. Conexiones (ESP32 DevKit V1) — resumen
La explicación detallada, con avisos de seguridad y fotos mentales del orden de los pines, está en `GUIA_ARMADO.md`.
Usen solo pines **ADC1** (32–39) para lo analógico: el ADC2 no funciona con el WiFi encendido. Todo se alimenta a **3V3**.

| Sensor | Pin del sensor | Pin del ESP32 |
|---|---|---|
| DHT22 | VCC / DATA / GND | 3V3 / **GPIO4** / GND |
| Humedad de suelo | VCC / AOUT / GND | 3V3 / **GPIO34** / GND |
| Lluvia FC-37 | VCC / **AO** / GND | 3V3 / **GPIO35** / GND |
| UV (opcional) | VCC / SIG(OUT) / GND | 3V3 / **GPIO32** / GND |

Si el DHT22 viene suelto (4 patas), pongan una resistencia de 10 kΩ entre VCC y DATA. El pin DO del módulo de lluvia no se usa.

## 3. Puesta en marcha (en orden)
1. **Backend (Vercel)** — agreguen estas variables en el proyecto del backend y hagan *Redeploy*:
   - `DEVICE_API_KEY`: una clave larga y aleatoria (`python -c "import secrets;print(secrets.token_urlsafe(24))"`).
   - Almacenamiento: en Vercel → *Storage* (o *Marketplace*) → **Upstash Redis** (plan gratis) → conectar al proyecto del backend.
     Eso añade `KV_REST_API_URL` y `KV_REST_API_TOKEN` (el backend acepta también `UPSTASH_REDIS_REST_URL/TOKEN`). Sin esto, las lecturas se pierden entre peticiones.
2. **Probar sin hardware:** `python hardware/tools/simulate_device.py --url https://TU-BACKEND.vercel.app --key TU_DEVICE_API_KEY`
   y revisar `https://TU-BACKEND.vercel.app/api/readings/latest` (`"online": true`).
3. **Arduino IDE:** instalar soporte de placas *esp32 by Espressif* y las librerías **DHT sensor library** y **Adafruit Unified Sensor**.
   Abrir `hardware/firmware/agrotec_node/agrotec_node.ino`, copiar `config.example.h` como `config.h` y completar WiFi, `API_URL` y `DEVICE_KEY`.
4. **Calibrar:** poner `CALIBRATION_MODE 1`, subir el sketch, abrir el Monitor Serie (115200) y anotar:
   sensor de suelo al aire (→ `SOIL_RAW_DRY`) y sumergido en agua (→ `SOIL_RAW_WET`); sensor de lluvia seco y mojado. Luego volver a `CALIBRATION_MODE 0` y subir de nuevo.
5. **Subir el sketch** con `CALIBRATION_MODE 0`. El LED azul de la placa se enciende cuando el envío fue exitoso (HTTP 201).
6. **En la app:** Inicio → interruptor **Sensor real**. Debe aparecer "● Sensor conectado" y los valores de la maqueta.

## 4. Problemas frecuentes
- **No conecta al WiFi:** el ESP32 solo usa redes **2.4 GHz** y no entra a redes con login web o WPA2-Enterprise (como suelen ser las de la universidad). Usen la **zona WiFi de un celular**.
- **El Monitor Serie muestra HTTP 401:** la `DEVICE_KEY` del `config.h` no coincide con `DEVICE_API_KEY` de Vercel. **503:** falta definir `DEVICE_API_KEY` en Vercel.
- **Valores de suelo en 0 % o 100 % fijos:** calibración (`SOIL_RAW_*`) o el sensor mal conectado a GPIO34.
- **"DHT22 read failed":** revisar cable de datos y alimentación.
- **La app dice "Sensor sin señal":** el nodo no envió en los últimos 30 s (apagado, sin WiFi o sin saldo de datos del hotspot).

## 5. Límites del plan gratuito
Con envíos cada 10 s: ~8.600 peticiones/día a Vercel y ~26.000 comandos/día a Upstash (gratis: ~500.000/mes). Para la semana de entrega sobra;
si lo dejan encendido todo el mes, suban `SEND_INTERVAL_MS` a 30 000.

## 6. Aviso de seguridad
El firmware usa `client.setInsecure()` (no valida el certificado HTTPS) para simplificar la demo. La `DEVICE_KEY` viaja cifrada igualmente, pero un atacante en la misma red podría suplantar al servidor.
Para producción hay que fijar el certificado raíz.

## 7. Pruebas de lo que sí se pudo verificar sin la placa
- `pytest` cubre la ingesta (clave, validación, estado en línea, historial, almacenamiento Upstash simulado).
- La matemática de calibración y el JSON del firmware (`conversions.h`) se probaron en un PC y el JSON generado lo acepta la API.
- **No se pudo compilar ni ejecutar el firmware en una placa real** desde este entorno: el primer *upload* puede requerir ajustes menores (versión de librerías, pines).
