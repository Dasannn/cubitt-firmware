# Obtención y análisis local del firmware

## 1. Obtener la APK

Con un teléfono propio conectado y autorizado por ADB:

```powershell
.\tools\pull_cubitt_apk.ps1
```

La salida queda en `apks/com.cubittpros.wear-<fecha>/`. También puedes usar una copia legítima de tu APK. Esta publicación no incluye la app ni sus binarios.

## 2. Extraer el asset

La APK analizada contenía este archivo ZIP interno:

```text
assets/flutter_assets/packages/creek_blue_manage/assets/images/zephyr.fw
```

Abre `base.apk` como ZIP y copia únicamente ese asset a `analysis/firmware_candidates/zephyr.fw`, creando antes la carpeta. Puede faltar o cambiar en otras versiones. No ejecutes los archivos extraídos.

## 3. Verificar y extraer el payload

```powershell
py tools/repack/repack_ota.py verify analysis/firmware_candidates/zephyr.fw
py tools/repack/repack_ota.py extract analysis/firmware_candidates/zephyr.fw analysis/firmware_candidates/zephyr_image.bin
Get-FileHash analysis/firmware_candidates/zephyr.fw -Algorithm SHA256
Get-FileHash analysis/firmware_candidates/zephyr_image.bin -Algorithm SHA256
```

Continúa con la extracción solo si `verify` termina correctamente.

| Archivo de referencia | Bytes | SHA256 |
|---|---:|---|
| `zephyr.fw` | 1252064 | `8d08723ed8dd12ab659a58edbd8a64ede3c416716f6ae49ccee9400714ebfd6a` |
| `zephyr_image.bin` | 1252000 | `f27f23ad76b697ecdc5f9563fdb7016574a6b2fc283da664685732c6cd781606` |

El payload empieza en `0x40`, no en `0x240`. El campo `0x0C` es el CRC32 del payload, no una fecha. El CRC32 de la muestra es `0x673bafc8`. Estos datos corrigen el reporte de extracción inicial, omitido de esta publicación por estar desactualizado.

## 4. Investigar

- Importa el payload como binario ARM little endian en Ghidra, con base `0x10010000`; revisa el modo Thumb y la tabla de vectores.
- Añade `analysis/ghidra_scripts/` al Script Manager para explorar las funciones documentadas. Las direcciones están fijadas para la muestra anterior.
- Lee [DFU_PROTOCOL.md](DFU_PROTOCOL.md) para el análisis de formatos y [BLE_WIRE_PROTOCOL.md](BLE_WIRE_PROTOCOL.md) para las observaciones de transporte.
- Usa `tools/adb_cubitt_inventory.ps1`, `tools/find_cubitt_firmware_files.ps1` y `tools/capture_cubitt_logcat.ps1` para generar evidencia local adicional. El capturador limpia el buffer logcat al iniciar; los reportes pueden contener datos personales y permanecen excluidos de Git.

## Pendiente

Confirmar el hardware exacto, obtener un respaldo completo y comprobar el bootloader y el método de recuperación antes de intentar instalar imágenes modificadas. Una coincidencia con un SDK de referencia o un CRC correcto no sustituye esas comprobaciones.
