# Cubitt firmware research

Investigación del firmware y protocolo BLE del **Cubitt VIVA Pro 2**: notas técnicas, herramientas de análisis y reempaquetado del contenedor OTA. Proyecto independiente, sin afiliación con Cubitt, Creek o Actions Technology.

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

## Archivos excluidos

No se distribuyen APKs, imágenes de firmware, SDKs de terceros, instalaciones de Ghidra, capturas, bases de datos, claves, certificados, logs, datos personales ni archivos generados. También se excluyen la app Gemini Bridge y los proxies de IA, ajenos al alcance del firmware. Las referencias históricas a `scratchpad/` corresponden a scripts no disponibles en esta publicación.

El `.gitignore` permite únicamente las rutas de documentación y código seleccionadas. Revisa cualquier nuevo documento antes de añadirlo: un reporte puede contener identificadores o credenciales aunque sea texto.

## Referencias

- SDK de referencia: https://github.com/lvgl/lv_port_actions_technology
- Investigación de otra plataforma Actions: https://github.com/ovsky/RE-ATS3603

Los recursos externos conservan sus condiciones de uso. Este repositorio no les atribuye una licencia ni redistribuye su contenido completo.

## Validación de esta publicación

Se verificaron los SHA256, tamaño y CRC32 de los archivos locales de referencia y se ejecutó `crc_filetran.py` con sus vectores existentes. Esto comprueba consistencia local, no equivalencia de todos los checksums con el dispositivo. No se ejecutaron flasheos, pruebas BLE/ADB ni scripts de Ghidra durante la preparación.
