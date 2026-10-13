# Cubitt VIVA Pro 2 — Ingeniería inversa

Documentación y herramientas del proceso de ingeniería inversa del firmware y del protocolo Bluetooth del **Cubitt VIVA Pro 2**. El objetivo es entender cómo la app se comunica con el reloj, cómo se empaqueta una actualización y qué falta para desarrollar modificaciones reproducibles. Proyecto independiente, sin afiliación con Cubitt, Creek o Actions Technology.

**Descargas:** actualmente no hay una versión modificada del firmware disponible para instalar. La guía permite extraer y estudiar la imagen original desde una APK propia. Los cambios locales de Gemini/DeepSeek pertenecen a la app Android y su proxy; no son una modificación del firmware del reloj.

## Qué puedes hacer con este repositorio

| Actividad | Cómo empezar | Resultado |
|---|---|---|
| Obtener la imagen original de referencia | [Guía de extracción](docs/FIRMWARE_RESEARCH.md) y una APK propia | Contenedor `zephyr.fw` y payload para análisis local |
| Comprobar integridad e identificar la muestra | `repack_ota.py verify` y SHA256 | Comparación de CRC32, longitudes y hashes documentados |
| Estudiar el código del firmware | Ghidra y `analysis/ghidra_scripts/` | Funciones, referencias y rutas de llamadas para la muestra analizada |
| Explorar Bluetooth del reloj | `cubitt_ble_recon.py` y [checklist BLE](docs/BLE_CHECKLIST.md) | Inventario de servicios, características y observación opcional de notificaciones |
| Entender la comunicación de la app | [Protocolo BLE](docs/BLE_WIRE_PROTOCOL.md) | Interpretación documentada de tramas C1 y transferencias D1–D4 |
| Experimentar con el contenedor sin conectarse al reloj | `repack_ota.py extract`, `build` y `patch` | Archivos locales reempaquetados con CRC32 del contenedor recalculado |
| Continuar la investigación | Comparar otra versión y documentar diferencias | Nueva evidencia sobre formatos, plataforma y transporte |

El reempaquetado produce un archivo de experimentación. Las herramientas publicadas no implementan un instalador de firmware modificado ni una integración lista para usar de Gemini/DeepSeek.

## Cómo se investigó

1. **Inspección de la app Android.** Se inventariaron el paquete y sus bibliotecas, se buscaron cadenas relacionadas con OTA, BLE y voz, y se revisaron los assets de la APK.
2. **Extracción y análisis del contenedor.** Se encontró `zephyr.fw` dentro de los assets y se contrastaron sus bytes, tamaños y CRC. La hipótesis inicial de un payload en `0x240` se corrigió a `0x40`.
3. **Análisis estático en Ghidra.** Se estudiaron funciones de transferencia, validación e items SDFS mediante descompilación y referencias cruzadas. Los scripts incluidos ayudan a repetir esa exploración sobre la misma muestra.
4. **Comparación con el SDK de plataforma.** Se relacionaron nombres, estructuras y rutas con el SDK público de Actions. Estas correspondencias orientan la investigación; no confirman por sí solas la configuración del reloj.
5. **Observación de BLE.** Las notas registran exploraciones GATT y capturas de comunicación app–reloj con instrumentación. Se distinguieron las tramas C1, el transporte crudo D1–D4 y los items SDFS. Los scripts originales de instrumentación y las capturas completas no están incluidos; se publican las observaciones técnicas y el explorador GATT.

Este proceso dejó correcciones y preguntas abiertas. Para interpretar los resultados hay que distinguir los bytes comprobados en la muestra, las observaciones registradas en el reloj y las hipótesis derivadas del SDK.

## Estado

- Se analizó una imagen `zephyr.fw` incluida en la APK de Cubitt Pro 2.1.11. Su presencia en la APK no demuestra que sea la imagen instalada o compatible con todas las unidades.
- El contenedor analizado tiene cabecera de `0x40` bytes, payload de 1.252.000 bytes y CRC32 `0x673bafc8`.
- Las notas identifican indicios de Zephyr y de la familia Actions ATS3085. La variante exacta del hardware y el mapa de particiones del reloj requieren confirmación independiente.
- Se documentaron servicios GATT y capturas de los protocolos C1 y file_tran D1–D4.
- No hay un firmware personalizado compilable ni un procedimiento de flasheo y recuperación validado. La aceptación de imágenes modificadas por el bootloader sigue pendiente.

Las notas de julio de 2026 conservan resultados e hipótesis de distintas etapas. Las afirmaciones históricas de «sin firma», «recuperación confirmada» o «cero riesgo» no constituyen una validación en hardware. Las correcciones posteriores dentro de cada documento prevalecen sobre las observaciones iniciales.

## Contenido

| Ruta | Contenido |
|---|---|
| [docs/FIRMWARE_RESEARCH.md](docs/FIRMWARE_RESEARCH.md) | Obtención local de la imagen y verificación reproducible |
| [docs/PLATFORM_SDK.md](docs/PLATFORM_SDK.md) | Correspondencias propuestas con el SDK Actions |
| [docs/DFU_PROTOCOL.md](docs/DFU_PROTOCOL.md) | Formatos de contenedor, imagen e items SDFS |
| [docs/BLE_WIRE_PROTOCOL.md](docs/BLE_WIRE_PROTOCOL.md) | Capturas e interpretación del protocolo BLE |
| [docs/BLE_OTA_ROUTE.md](docs/BLE_OTA_ROUTE.md) | Investigación histórica de la ruta OTA |
| [docs/BLE_CHECKLIST.md](docs/BLE_CHECKLIST.md) | Registro manual de servicios BLE |
| [docs/APK_ANALYSIS.md](docs/APK_ANALYSIS.md) | Inspección local de la APK |
| [analysis/reports/fase1_signature_verdict.md](analysis/reports/fase1_signature_verdict.md) | Evidencias históricas sobre integridad y firma |
| `tools/repack/` | Verificación, extracción y reempaquetado; checksums experimentales |
| `tools/ble/` | Escaneo GATT y observación de notificaciones con Bleak |
| `tools/*.ps1` | Inventario ADB, extracción de APK y búsqueda de firmware/logs |
| `analysis/ghidra_scripts/` | Scripts de Ghidra con direcciones específicas de la imagen analizada |

## Uso local

```powershell
git clone https://github.com/Dasannn/cubitt-firmware.git
cd cubitt-firmware
```

Python 3 para reempaquetado; PowerShell y Android SDK Platform Tools para los scripts ADB. Estos últimos buscan `adb.exe` en `%LOCALAPPDATA%\Android\Sdk\platform-tools`. Ejecuta los comandos desde la raíz del repositorio.

```powershell
py tools/repack/crc_filetran.py
py tools/repack/repack_ota.py verify analysis/firmware_candidates/zephyr.fw
py tools/repack/repack_ota.py extract analysis/firmware_candidates/zephyr.fw analysis/firmware_candidates/zephyr_image.bin
```

Obtén primero tu archivo `.fw` siguiendo [la guía de extracción](docs/FIRMWARE_RESEARCH.md). Los comandos `build` y `patch` del reempaquetador producen archivos locales; recalcular el CRC del contenedor no valida el contenido ni garantiza que arranque. Usa siempre una salida distinta del original.

Para explorar BLE, instala la dependencia opcional y escanea:

```powershell
py -m pip install bleak
py tools/ble/cubitt_ble_recon.py --scan
py tools/ble/cubitt_ble_recon.py --addr AA:BB:CC:DD:EE:FF --observe 0
```

Sustituye la dirección de ejemplo por la de tu reloj. `--observe 0` desactiva las suscripciones; el valor por defecto es 20 segundos. Suscribirse a notificaciones configura el descriptor CCCD aunque no envíe datos de aplicación ni comandos de actualización.

Los scripts de Ghidra usan la base `0x10010000` y direcciones de la imagen indicada en la guía. Sus resultados no son transferibles automáticamente a otras versiones.

## Cómo contribuir

Puedes abrir un issue o un pull request con correcciones, diferencias entre versiones o resultados reproducibles. Indica el modelo, la versión de la app, el SHA256 de la imagen, la herramienta utilizada y los pasos para repetir la observación. Distingue el resultado observado de su interpretación.

Los siguientes pasos son confirmar la variante de hardware, contrastar los checksums con más muestras, estudiar el bootloader real y validar un respaldo y una recuperación antes de probar firmware modificado. Para compartir evidencia, usa extractos mínimos anonimizados; elimina direcciones de tus dispositivos, contactos, tokens y otros datos personales.

## Archivos excluidos

No se distribuyen APKs, imágenes de firmware, SDKs de terceros, instalaciones de Ghidra, capturas, bases de datos, claves, certificados, logs, datos personales ni archivos generados. También se excluyen la app Gemini Bridge y los proxies de IA, ajenos al alcance del firmware. Las referencias históricas a `scratchpad/` corresponden a scripts no disponibles en esta publicación.

El `.gitignore` permite únicamente los archivos revisados, por nombre exacto. Revisa cualquier nuevo documento antes de permitirlo: un reporte puede contener identificadores o credenciales aunque sea texto. Esta exclusión no protege contra secretos añadidos a un archivo ya versionado ni contra `git add -f`.

## Referencias

- SDK de referencia: https://github.com/lvgl/lv_port_actions_technology
- Investigación de otra plataforma Actions: https://github.com/ovsky/RE-ATS3603

Los recursos externos conservan sus condiciones de uso. Este repositorio no les atribuye una licencia ni redistribuye su contenido completo.

## Validación de esta publicación

Se verificaron los SHA256, tamaño y CRC32 de los archivos locales de referencia y se ejecutó `crc_filetran.py` con sus vectores existentes. Esto comprueba consistencia local, no equivalencia de todos los checksums con el dispositivo. No se ejecutaron flasheos, pruebas BLE/ADB ni scripts de Ghidra durante la preparación.
