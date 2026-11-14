# Guía paso a paso para armar la maqueta AgroTec (desde cero)

No hace falta saber electrónica ni soldar. Si siguen los pasos en orden, funciona. **Lean los avisos de seguridad primero.**

> **Versión del grupo: SIN sensor UV.** La maqueta lleva 3 sensores reales: **humedad de suelo, DHT22 (temperatura y humedad del aire) y lluvia**.
> El UV y el pH quedan simulados y la app los marca como **SIM**. En todo lo que sigue, **ignoren el UV** (solo se usa la sección 4.5 si algún día consiguen uno).

## Reparto sugerido para el grupo de 3
Cada quien hace su parte **y la sube a GitHub desde su propia cuenta** (así los commits reflejan el trabajo real de cada uno). Pueden cambiar los roles: lo importante es que las tres partes se hagan.

| Persona | Responsabilidad | Qué entrega (commit propio) |
|---|---|---|
| **Juan** (Juanda-11) | **Nube y verificación:** variables en Vercel (`DEVICE_API_KEY`, Upstash), fusionar PRs, probar con el simulador, revisar que la app muestre "Sensor real" | `docs`: notas de despliegue y capturas de la app en modo real (`hardware/docs/`) |
| **Brayan** (brayanckr) | **Electrónica y firmware:** armar el circuito (sección 4), instalar Arduino IDE, calibrar y subir el firmware (secciones 3 y 5) | `hardware/docs/calibration-results.md` con los valores medidos (`SOIL_RAW_*`, `RAIN_RAW_*`) y foto del cableado |
| **Mario** (MarioZaMu) | **Maqueta y demostración:** armar la maqueta física (sección 7), ensayar el guion (sección 8) y preparar el plan B | `hardware/docs/demo-checklist.md` con el guion ajustado y fotos de la maqueta |

**Cómo subir cada parte (Brayan y Mario ya son colaboradores del repo):**
```bash
git clone https://github.com/Juanda-11/Proyecto-final-AgroTec---Backend.git
cd Proyecto-final-AgroTec---Backend
git checkout -b feature/tu-nombre-tarea        # una rama por persona
# ...crean o editan sus archivos...
git add hardware/docs/tu-archivo.md
git commit -m "docs(hardware): calibration results and wiring photo"   # mensaje en inglés, pequeño y claro
git push -u origin feature/tu-nombre-tarea
# en GitHub: "Compare & pull request" -> otro integrante lo revisa y lo fusiona
```
Un commit por cambio real (no mezclen todo en uno). **No** suban `config.h` (tiene claves): ya está ignorado por git.

### Lista de verificación antes de empezar (¿ya tienen todo?)
- [ ] ESP32 DevKit V1 + cable USB **de datos**
- [ ] Sensor de humedad de suelo capacitivo v1.2
- [ ] DHT22 (módulo de 3 pines)
- [ ] Módulo de lluvia FC-37 (placa + módulo con `AO`)
- [ ] Protoboard 830 puntos y cables dupont macho-macho, macho-hembra y hembra-hembra
- [ ] Un celular con **zona WiFi** (2.4 GHz) y un power bank o cargador
- [ ] Matera con tierra, base de la maqueta, caja plástica, silicona/cinta
- [ ] *(Opcional)* sensor UV: **no es necesario**

## 0. Avisos importantes (2 minutos)
1. **Armen siempre con el ESP32 desconectado del USB.** Conecten el cable USB solo cuando todo esté revisado.
2. Todos los sensores se alimentan a **3V3** (el pin marcado `3V3`). **Nunca** los conecten a `VIN` ni a `5V`: pueden dañar el ESP32.
3. **El agua solo toca la parte de abajo del sensor de suelo y la placa de lluvia.** El ESP32, la protoboard y los módulos se mantienen secos.
4. **Guíense por las etiquetas impresas en cada módulo** (`VCC`, `GND`, `OUT`/`AO`/`DATA`…), no por el orden de los pines: cambia entre fabricantes.
5. Si algo huele a quemado o se calienta mucho, desconecten el USB de inmediato.

## 1. Qué debe tener a la mano
- ESP32 DevKit V1 (30 pines), cable USB de datos, computador con Arduino IDE.
- Protoboard de 830 puntos.
- Cables dupont de los **3 tipos**: macho-macho (M-M), macho-hembra (M-H) y hembra-hembra (H-H). Un paquete de 120 trae los tres.
- Los 3 sensores: humedad de suelo capacitivo, DHT22 y módulo de lluvia (placa + módulo con comparador). El sensor UV es opcional (4.5).
- Cinta o silicona caliente, una matera con tierra.

## 2. Conozcan la placa y la protoboard
**ESP32 DevKit V1 (30 pines), vista desde arriba con el USB hacia ABAJO.** Las etiquetas están impresas al lado de cada pin (`D34` = GPIO34):

```
        IZQUIERDA                      DERECHA
   EN                                        D23
   VP (36)                                   D22
   VN (39)                                   TX0
 ► D34   <- humedad de suelo                 RX0
 ► D35   <- lluvia                           D21
 ► D32   <- UV (SIN USAR en nuestra versión)  D19
   D33                                       D18
   D25                                       D5
   D26                                       TX2
   D27                                       RX2
   D14                                  ◄ D4    -> DHT22
   D12                                       D2  (LED azul de la placa)
   D13                                       D15
 ► GND   <- cualquiera de los GND         ◄ GND
   VIN   <- NO USAR                       ◄ 3V3  -> alimentación de TODOS los sensores
            [ USB ]
```
Si su placa tiene otro orden, **busquen las etiquetas `D34`, `D35`, `D32`, `D4`, `3V3` y `GND`** en la placa: son los únicos 6 pines que se usan.

**La protoboard:**
- Los **huecos de una misma columna (a–e, o f–j) están conectados entre sí**. Los de columnas distintas, no. Los dos lados del canal central tampoco se conectan.
- Las **dos líneas largas de los bordes (riel rojo `+` y riel azul `−`)** están conectadas en toda su longitud. Usaremos el riel rojo para **3V3** y el azul para **GND**.
- Algunas protoboards tienen el riel partido a la mitad: si un sensor no recibe energía, prueben usar el otro extremo del riel.

## 3. Instalen el software y prueben el ESP32 solo (antes de conectar nada)
1. Instalen **Arduino IDE 2.x** (arduino.cc).
2. *Archivo → Preferencias → "Gestor de URLs adicionales de tarjetas"*: peguen `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
3. *Herramientas → Placa → Gestor de tarjetas*: busquen **esp32** e instalen "esp32 by Espressif Systems".
4. *Herramientas → Gestionar bibliotecas*: instalen **DHT sensor library** (de Adafruit) y, cuando pregunte, también **Adafruit Unified Sensor**.
5. Conecten el ESP32 al USB. Si el computador no lo reconoce, instalen el driver **CP210x** o **CH340** (depende del chip pequeño junto al USB).
6. *Herramientas → Placa → ESP32 Arduino → ESP32 Dev Module* y *Puerto* → el `COMx` nuevo.
7. Abran *Archivo → Ejemplos → 01.Basics → Blink* y pulsen *Subir*. Si aparece "Connecting........", **mantengan pulsado el botón `BOOT`** de la placa hasta que empiece a subir.
8. Si el LED azul parpadea, la placa funciona. **Desconecten el USB.**

## 4. Armado, sensor por sensor
Para cada sensor: se ubica el módulo en una zona propia de la protoboard, se conectan **alimentación, tierra y señal**. Voy a usar este código de colores (sugerido): **rojo = 3V3, negro = GND, otros colores = señal**.

### 4.1 Distribución de energía (hagan esto primero)
| De | A | Cable |
|---|---|---|
| Pin `3V3` del ESP32 | Riel **rojo (+)** de la protoboard | M-H (la punta hembra al ESP32) |
| Pin `GND` del ESP32 | Riel **azul (−)** de la protoboard | M-H |

Dejen el ESP32 sobre la mesa **al lado** de la protoboard (no hace falta enchufarlo en ella).

### 4.2 DHT22 (temperatura y humedad del aire) → pin D4
1. El módulo de 3 pines trae etiquetas: `+` (o VCC), `OUT` (o DATA) y `−` (o GND).
2. Claven sus 3 pines en una fila de la protoboard, en 3 columnas contiguas (por ejemplo columnas 10, 11 y 12 en la fila `a`).
3. Cables:
   - riel **rojo** → columna del `+` (M-M)
   - riel **azul** → columna del `−` (M-M)
   - columna de `OUT` → pin **D4** del ESP32 (M-H)

### 4.3 Sensor de humedad de suelo → pin D34
1. El cable del sensor tiene 3 hilos: `VCC`, `GND` y `AOUT` (señal). Si el sensor trae un conector blanco, conéctenlo al cable que viene incluido.
2. Mismos pasos que el DHT22, en otras 3 columnas libres (por ejemplo 20, 21 y 22):
   - riel **rojo** → `VCC`
   - riel **azul** → `GND`
   - `AOUT` → pin **D34** del ESP32
3. **Solo la parte inferior del sensor, hasta la línea impresa, va dentro de la tierra.** Sellen el borde superior con silicona o esmalte de uñas para que no entre humedad a los componentes.

### 4.4 Módulo de lluvia FC-37 → pin D35
1. Tiene **dos partes**: la placa con pistas (el sensor, que se moja) y el módulo pequeño con un chip (el comparador). Se unen con un cable de 2 hilos; el módulo tiene 4 pines: `VCC`, `GND`, `DO`, `AO`.
2. Usen **`AO`** (analógico). **`DO` no se conecta**.
   - riel **rojo** → `VCC`
   - riel **azul** → `GND`
   - `AO` → pin **D35** del ESP32
3. Pongan la placa **inclinada** para que el agua escurra y se pueda secar.

### 4.5 Sensor UV → **No lo usaremos** (saltar esta sección)
Nuestra maqueta **no lleva sensor UV**: no conecten nada al pin D32 y en `config.h` dejen `#define UV_SENSOR 0` (el firmware ya lo trae así).
La app mostrará el UV con la etiqueta **SIM** (simulado), y es lo correcto.

*Solo si algún día consiguen uno:* el GUVA-S12SD o el UVM-30A (`UV_SENSOR 1`) y el ML8511/GY-8511 (`UV_SENSOR 2`, además con el pin `EN` al riel rojo)
se conectan con `VCC` al riel rojo, `GND` al azul y la salida a **D32**. Eviten los módulos I2C (VEML6075, LTR390): este firmware no los soporta.

### 4.6 Revisión final (no se salten esto)
Marquen cada línea cuando la confirmen con la vista:
- [ ] `3V3` del ESP32 → solo al riel **rojo**. `GND` → solo al riel **azul**. Nada conectado a `VIN`.
- [ ] Los 3 sensores tienen **un** cable rojo, **uno** azul y **uno** de señal.
- [ ] Señales: DHT22 → **D4**, suelo → **D34**, lluvia → **D35**. **D32 queda sin conectar.**
- [ ] Ningún cable de señal toca los rieles ni otra columna.
- [ ] Todo está seco.

## 5. Calibración (15 minutos, una sola vez)
1. En el repo del backend, carpeta `hardware/firmware/agrotec_node/`, copien `config.example.h` como **`config.h`** (en la misma carpeta) y ábranlo.
2. Pongan `#define CALIBRATION_MODE 1`. Dejen WiFi y claves como están por ahora.
3. Abran `agrotec_node.ino` en Arduino IDE, *Subir*, y abran el **Monitor Serie** (esquina superior derecha, velocidad **115200**). Verán una línea por segundo:
   `soil raw=… | rain raw=… | uv mV=… | temp=… | air hum=…`
4. **Suelo:** anoten `soil raw` con el sensor **al aire, seco** → eso es `SOIL_RAW_DRY` (suele ser ~3000–3500). Luego sumerjan **solo la punta, hasta la línea**, en un vaso de agua → `SOIL_RAW_WET` (~1200–1600).
5. **Lluvia:** anoten `rain raw` con la placa seca (`RAIN_RAW_DRY`, ~4095) y con unas gotas cubriendo las pistas (`RAIN_RAW_WET`).
6. Escriban esos 4 números en `config.h` (en `uv mV` verán 0: normal, no hay sensor UV), pongan `CALIBRATION_MODE 0` y rellenen:
   - `WIFI_SSID` y `WIFI_PASSWORD`: **usen la zona WiFi de un celular** (2.4 GHz). El WiFi de la universidad normalmente no funciona con el ESP32.
   - `API_URL`: la URL de su backend en Vercel, sin `/` final.
   - `DEVICE_KEY`: la misma clave que pusieron en la variable `DEVICE_API_KEY` de Vercel.
7. *Subir* de nuevo. En el Monitor Serie deben ver `POST … -> 201`. El LED azul de la placa se enciende si el envío fue exitoso.

## 6. Verificar de extremo a extremo
1. Abran `https://TU-BACKEND.vercel.app/api/readings/latest`: debe mostrar `"online": true` y los valores.
2. En la app, pantalla **Inicio → Sensor real (ESP32)**: debe decir "Nodo esp32-01 en línea" y los sensores aparecen con la etiqueta **REAL**.

## 7. Cómo armar la maqueta física (propuesta sencilla)
- **Base:** una tabla o acrílico de unos 40×30 cm. Pueden pintar un letrero "AgroTec · Nariño".
- **Matera con tierra y una planta** en el centro; el sensor de suelo clavado a unos 5 cm de la planta.
- **DHT22 y UV** en un palito o soporte, a unos 20 cm sobre la planta, con el UV mirando al cielo y el DHT22 a la sombra.
- **Placa de lluvia** en una esquina, inclinada.
- **Electrónica** (ESP32 + protoboard) dentro de una cajita plástica con orificios para los cables, fuera del alcance del agua. Fijen todo con silicona caliente o cinta de doble cara.
- **Energía:** cable USB a un power bank o cargador.

## 8. Guion de demostración (para la sustentación)
| Qué hacen | Qué se ve en la app |
|---|---|
| Echan agua a la matera | La humedad del suelo sube en unos segundos |
| Dejan secar / retiran el sensor | La humedad baja; si cruza el umbral, aparece una alerta en la cola |
| Respiran cerca del DHT22 | La temperatura sube |
| Echan unas gotas en la placa de lluvia | La probabilidad de lluvia sube |
| Pulsan "Analizar mi cultivo" | La IA explica el estado con los datos **reales** |
| Apagan el ESP32 | A los ~30 s la app dice "Nodo sin señal" |

> En la pantalla Inicio, humedad del suelo y temperatura salen con la etiqueta **REAL**; **pH y UV salen como SIM** (simulados). Díganlo en la sustentación: "la maqueta mide en real suelo, temperatura, humedad del aire y lluvia; pH y UV están simulados y se pueden añadir con más sensores".

## 9. Si algo no funciona
| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El ESP32 no aparece como puerto | Cable solo de carga o falta el driver | Usen otro cable USB **de datos**; instalen CP210x o CH340 |
| "Connecting......" no termina al subir | La placa no entra a modo carga | Mantengan pulsado `BOOT` mientras sube |
| `DHT22 read failed` | Cable de datos mal puesto o sin alimentación | Revisen D4, `+` y `−`; reconecten |
| Suelo siempre 0 % o 100 % | Calibración o cable en otro pin | Repitan el paso 5; confirmen D34 |
| Lluvia siempre 100 % o 0 % | Falta calibrar o usaron `DO` en vez de `AO` | Usen `AO` → D35; calibren |
| `WiFi connection failed` | Red 5 GHz, con login web, o clave mal escrita | Usen la zona WiFi del celular en 2.4 GHz |
| `POST … -> 401` | `DEVICE_KEY` ≠ `DEVICE_API_KEY` | Que sean exactamente iguales y redespliegue Vercel |
| `POST … -> 503` | Falta definir `DEVICE_API_KEY` en Vercel | Agréguenla y redespliegen |
| `POST … -> -1` / `-11` | Sin internet o URL mal escrita | Revisen `API_URL` (con `https://`, sin `/` final) |
| La app dice "Sin señal" aunque el Serial muestra 201 | La app apunta a otro backend | Revisen `EXPO_PUBLIC_API_URL` en el frontend y redespliéguenlo |

## 10. Plan sugerido para la semana (con responsables)
| Día | Tarea | Quién |
|---|---|---|
| 1 | Verificar que tienen todas las piezas. Instalar Arduino IDE y subir el *Blink* (sección 3) | Brayan |
| 1 | Variables en Vercel (`DEVICE_API_KEY` + Upstash), redesplegar y probar con `simulate_device.py` | Juan |
| 2 | Armar el circuito de los 3 sensores (sección 4) y revisar con la lista 4.6 | Brayan (con Mario de apoyo) |
| 2 | Conseguir base, matera, tierra, caja y silicona | Mario |
| 3 | Calibrar y subir el firmware final (sección 5); registrar los valores en `calibration-results.md` | Brayan |
| 3 | Verificar de extremo a extremo (sección 6): `/api/readings/latest` y la app en "Sensor real" | Juan |
| 4 | Armar la maqueta física (sección 7) y fijar el cableado | Mario y Brayan |
| 5 | Ensayar el guion de demostración (sección 8); tomar fotos y capturas | Todos |
| 6 | Ensayo general completo con zona WiFi y power bank; corregir fallos | Todos |
| 7 | Entrega. Lleven un ESP32 de repuesto (si lo tienen) y el simulador de dispositivo como plan B | Todos |
