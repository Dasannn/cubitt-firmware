# Fase 1 - Veredicto de firma / secure-boot (preliminar, estatico)

> Nota de publicacion: registro historico de investigacion, con hipotesis pendientes.
> Los CRC observados no demuestran que el bootloader acepte firmware modificado.
> El mapa del SDK, la recuperacion ADFU y el flasheo completo no se han validado en el reloj.
> Las rutas a binarios, capturas y `scratchpad/` son referencias locales no distribuidas.
> Consulta el README para el alcance actual.

Fecha: 2026-07-06
Objetivo: determinar si la imagen OTA del Cubitt Viva Pro 2 esta firmada y si eso bloquea
flashear una imagen modificada.

## Archivos analizados

- `analysis/firmware_candidates/zephyr.fw` - contenedor OTA `5A8778A5`, 1,252,064 B.
- `analysis/firmware_candidates/zephyr_image.bin` - **carve corregido** = `fw[0x40:]`, 1,252,000 B,
  SHA256 `f27f23ad76b697ecdc5f9563fdb7016574a6b2fc283da664685732c6cd781606`. Es la imagen ejecutable.
- `analysis/extracted/arm64/lib/arm64-v8a/libapp.so` - cliente OTA (Dart AOT).

Nota: el `zephyr.bin` anterior estaba desfasado 0x200 (empezaba en la sub-cabecera `ACTHHTCA`
interna en vez del inicio real de la imagen). El correcto es `zephyr_image.bin`.

## Estructura confirmada del contenedor

Cabecera = **0x40 bytes** (no 0x240). Layout:

| offset | bytes | significado |
|--------|-------|-------------|
| 0x00 | `5A 87 78 A5` | magic contenedor |
| 0x0C | `C8 AF 3B 67` | **CRC32 del payload** (ver abajo) |
| 0x10 | `A0 1A 13 00` | longitud payload = 0x131AA0 = 1,252,000 |
| 0x14 | `A0 1A 13 00` | longitud (duplicada) |
| 0x20 | `zephyr.bin\0` | nombre interno |
| 0x40.. | imagen | vector table Cortex-M + codigo (load 0x10010000) |

La cabecera de 0x40 no contiene ningun bloque de 16 B (CMAC) ni 256 B (RSA-2048). Solo magic,
CRC, longitud y nombre.

## Evidencia clave

1. **Integridad = CRC32, no firma.**
   `crc32(fw[0x40:]) = 0x673BAFC8` == campo en `0x0C`. Coincidencia exacta. El unico control de
   integridad que viaja en el paquete OTA es un CRC32, recomputable con `zlib.crc32` tras cualquier
   modificacion.

2. **Imagen en texto plano.** Entropia global 7.084 (mezcla codigo/datos, no cifrado). Tabla de
   vectores ARM valida en `payload[0]`: SP=0x01002140 (SRAM), reset=0x10075671 (thumb, dentro de la
   imagen). Load base 0x10010000.

3. **Sin firma anexada.** Barrido de entropia por ventanas: maximo 256 B = 7.56 (zonas comprimidas
   normales, p.ej. DSP/recursos), sin ningun bloque aislado ~8.0 que delatara una firma RSA/ECDSA.
   Los ultimos 128 B de la imagen son tablas de punteros (entropia 3.1), no un MAC.

4. **`AES CMAC` existe en codigo pero no como firma de imagen.** Unica referencia: string
   "Unable to setup AES CMAC". Si el arranque exigiera un CMAC sobre la imagen, el paquete OTA
   tendria que transportarlo (el servidor no puede firmar en el reloj). El paquete solo lleva CRC.

5. **`efuse` = calibracion, no llaves.** Referencias: "get efuse rf", "get efuse power",
   "get efuse avdd" -> valores de calibracion RF/potencia, no fusibles de clave secure-boot.

6. **Cliente OTA (libapp.so):** simbolos `_checkNeedOta`, `checkUpgrade`, `ACTIVE_OTA_CHECK`,
   `check_firmware_upgrade`. El unico `hmac-sha256 ... signature=` es firmado de requests HTTP a la
   API (auth de transporte), no del firmware. RSA (PointyCastle) esta empacado pero sin uso evidente
   en el flujo OTA.

## Razonamiento decisivo

El paquete OTA actualiza **solo la particion `app`** (sub-cabecera `ACTHHTCA` = "app", load
0x10010000) y viaja con **solo un CRC32**. Si el bootloader on-device exigiera un MAC/firma por
imagen, el propio OTA legitimo no podria actualizar la app sin transportar ese MAC actualizado (y el
reloj no puede firmarlo solo). Como el paquete no lo lleva, la conclusion logica es que **no hay un
gate criptografico por imagen sobre la particion app**. De lo contrario, cada OTA oficial brickearia
el reloj.

## Veredicto

**(a) leaning fuerte: integridad por CRC32, sin firma criptografica.** Una imagen `app` modificada,
con el CRC32 recomputado y la cabecera 0x40 reempacada, es muy probablemente aceptada por la ruta
DFU/boot.

Incertidumbre residual (honesta): el **bootloader/mbrec on-device NO esta en este archivo** (este
archivo es la app que el bootloader carga). La confirmacion 100% de que el bootloader no valida un
CMAC antes del salto requiere una de dos:
- RE en Ghidra de la ruta de verificacion (Fase 3), o
- dump completo del flash por ADFU (Fase 5) para inspeccionar mbrec/bootloader.

Confianza actual: **media-alta** de que no hay firma que bloquee el reflasheo de una app modificada.

## Proximo paso recomendado

1. Fase 3 en Ghidra: cargar `zephyr_image.bin` en base 0x10010000, ubicar el cargador/salto a la app
   y confirmar que no hay verificacion CMAC/firma previa.
2. Fase 5 (requiere el reloj y tu autorizacion): dump ADFU para ver el bootloader real y respaldar.

## Actualizacion Fase 3 (Ghidra) + Fase 2 (SDK) - veredicto CONFIRMADO

Ghidra headless (4655 funciones, `zephyr_image.bin`) confirma que la ruta de actualizacion/boot es
CRC, no firma:
- DFU por bloque: `[file_tran_port_dfu]: write_crc32:%02x` (FUN_10123844).
- Validacion de imagen/particion en capas por CRC: `bad head crc`, `bad data crc`,
  `invalid header crc 0x%x != hdr->crc 0x%x`, `item crc error`, `psn%d: crc check error`.
- `reboot adfu` / `reboot [adfu]` presentes -> ruta ADFU de recuperacion confirmada.
- Primitivas presentes pero fuera del gate de imagen: CRC32 tables (`0x10130930`, `0x1006d910`),
  AES sbox (`0x1006e4b4`), SHA256 K (`0x1011a1d8`), y AES-CMAC (FUN_100b389c) que calcula un
  hash/token de 8 bytes con uso aparte (no verifica la imagen).

SDK (Fase 2): la plataforma Actions ATS3085 soporta firma RSA como **opcion de build**
(`bootloader/boards/arm/ats3085s_dev_watch_sign`, `soc_rsa.c`). La evidencia binaria dice que Cubitt
uso la variante **no-sign** (solo CRC).

Veredicto final: **(a) CONFIRMADO - integridad por CRC en capas, sin firma. Confianza ALTA.**
Para flashear una app modificada: recomputar TODOS los CRC (contenedor 0x0C + header + data + items)
y reempacar. Unico punto no observable en estatico: el mbrec/ROM on-device (se cierra con dump ADFU,
Fase 5). Ver `docs/PLATFORM_SDK.md`.
