# Ruta 1 - Flasheo BLE (sin abrir el reloj) - GATT + protocolo

> Nota de publicacion: registro historico de investigacion, con hipotesis pendientes.
> Los CRC observados no demuestran que el bootloader acepte firmware modificado.
> El mapa del SDK, la recuperacion ADFU y el flasheo completo no se han validado en el reloj.
> Las rutas a binarios, capturas y `scratchpad/` son referencias locales no distribuidas.
> Consulta el README para el alcance actual.

Fecha: 2026-07-06
Fuentes: SDK `application/bt_watch/src/ota/ota_app_background.c`,
`application/bt_watch/src/vendor/vendor_app.c`, y bytes confirmados en
`analysis/firmware_candidates/zephyr_image.bin`. Todo verificado en binario, no supuesto.

## 1. Servicios GATT que el reloj expone (confirmados en el binario)

Ambas tablas de atributos GATT estan presentes en el firmware (UUID de 128 bits guardado en orden
LE/invertido, tablas contiguas en 0x12f3xx-0x12f5xx de `zephyr_image.bin`).

### A. Servicio OTA (ruta de flasheo) - de `ota_app_background.c`
| Rol | UUID | Propiedades | offset en binario (LE) |
|-----|------|-------------|------------------------|
| Service | `e49a25f8-f69a-11e8-8eb2-f2801f1b9fd1` | Primary | 0x12f3a9 |
| RX (escritura app->reloj) | `e49a25e0-f69a-11e8-8eb2-f2801f1b9fd1` | Write / WriteNoRsp | 0x12f419 |
| TX (notify reloj->app) | `e49a28e1-f69a-11e8-8eb2-f2801f1b9fd1` | Notify | 0x12f4ad |
| CCC | `2902` (estandar) | - | - |

Este es el backend `ota_backend_bt` del SDK. Transporta el **contenedor OTA 5A8778A5 completo como
stream transparente** hacia el reloj; el modulo `ota_upgrade` del reloj lee el contenedor, valida el
CRC32, lo escribe en el area TEMP y reinicia. Tambien existe alias SPP `00006666-0000-1000-8000-00805f9b34fb`.

### B. Servicio vendor / data (sync + disparo de OTA) - de `vendor_app.c`
| Rol | UUID | Propiedades | offset en binario (LE) |
|-----|------|-------------|------------------------|
| Service | `f48a23c0-f69a-11e8-8eb2-f2801f1b9fd1` | Primary | 0x12f539 |
| RX (write) | `f48a24c1-f69a-11e8-8eb2-f2801f1b9fd1` | Write / WriteNoRsp | 0x12f589 |
| TX (notify) | `f48a25c2-f69a-11e8-8eb2-f2801f1b9fd1` | Notify | 0x12f313 |
| CCC | `2902` | - | - |

Canal de datos normal (TLV: `tlv_pack(type, len, value)`). Por aqui la app hace sync y, segun el
modelo, dispara el modo OTA (`file_tran` / `protocol_file_tran`).

### Nota sobre la app Cubitt
`libapp.so` (Dart AOT, flutter_blue_plus) solo expone como string el servicio `00000ff0-...` y un
`258eafa5-...`; los UUID de 128 bits de arriba los arma en runtime desde bytes, por eso no aparecen
como texto.

### C. GATT REAL del reloj en modo normal (scan live 2026-07-06, AA:BB:CC:DD:EE:FF)
MTU negociada = 23 (default). Servicios vendor presentes:

| Service | Char | Handle | Props | Rol |
|---------|------|--------|-------|-----|
| `00000ff0` | `00000001` | 0x0025 | write / wnr | **file_tran RX (DFU, app->reloj)** |
| `00000ff0` | `00000002` | 0x0027 | notify | **file_tran TX (reloj->app)** |
| `0000ffd0` | `0000ffd1` | 0x001c | write / wnr | vendor control write |
| `0000ffd0` | `0000ffd2` | 0x001e | notify | vendor control notify |
| `0000ffd0` | `0000ffd3` | 0x0021 | write / wnr / notify | vendor control rw |

Mas estandar: 1800 (GAP), 1801 (GATT), 180a (DevInfo), 180d (HeartRate), 180f (Battery).

**Los servicios OTA 128-bit `e49a25f8` y `f48a23c0` NO aparecen en modo normal.** Se registran solo
cuando el reloj entra en modo OTA (la app lo dispara y el reloj reinicia / rota su tabla GATT). Por
tanto el canal de trabajo en modo normal es el `00000ff0` (protocol_file_tran = el parser DFU
`FUN_100cfe94` que ya mapeamos: 'I'/0xFF/'Z', crc8 por bloque, trozos de 128 B).

Idle: sin trafico notify en 25s (el reloj solo emite al sincronizar/transferir).

## 2. Contenedor OTA 5A8778A5 (verificado byte a byte)

Cabecera de 0x40 bytes. Payload = imagen app raw cargada en 0x10010000 (vector table Cortex-M).

| offset | tam | campo | valor en zephyr.fw |
|--------|-----|-------|--------------------|
| 0x00 | 4 | magic | `5A 87 78 A5` |
| 0x0C | 4 | **CRC32 del payload (zlib)** | `0x673bafc8` (verificado) |
| 0x10 | 4 | longitud payload | `0x131aa0` = 1252000 |
| 0x14 | 4 | longitud payload (copia) | `0x131aa0` |
| 0x20 | 16 | nombre | `zephyr.bin` |
| 0x40 | .. | payload (imagen app) | @0x10010000 |

Gate de integridad de este contenedor = **un solo CRC32 en 0x0C**. Sin firma, sin CMAC. Reempacar =
modificar payload y recomputar ese CRC32 (y las longitudes si cambia el tamano). Ver
`tools/repack/repack_ota.py`.

## 3. Flujo end-to-end de la Ruta 1

### Fase estatica (sin reloj) - HECHO / en curso
1. UUIDs GATT extraidos (arriba).
2. Packer del contenedor listo (`repack_ota.py`), CRC32 verificado contra el original.
3. Cliente de recon `bleak` listo (`tools/ble/cubitt_ble_recon.py`).

### Fase recon (con reloj, SOLO LECTURA - cero riesgo)
4. `cubitt_ble_recon.py`: escanea, conecta, vuelca toda la tabla GATT (servicios, caracteristicas,
   propiedades, handles, descriptores) y se suscribe a las TX notify (`e49a28e1`, `f48a25c2`) para
   observar que emite el reloj. **No escribe nada.** Sirve para confirmar que el servicio OTA existe,
   sus handles reales, y la MTU negociada.

### Fase push (con reloj, ESCRITURA - requiere autorizacion explicita por paso)
5. Modificar payload (empezar por algo minimo y reversible), repack con `repack_ota.py`.
6. Suscribir TX notify, negociar MTU, escribir el contenedor en trozos de MTU al RX (`e49a25e0`),
   observando las notify de flujo/PRN del reloj.
7. El reloj valida CRC32 -> escribe en TEMP -> reinicia -> activa.
8. Verificar en pantalla. Si falla: TEMP no toco la app viva, o arranca la particion `recovery`.

## 4. Seguridad de la ruta (honesto)

- **Staging TEMP** (`ota_embed=TEMP` en `fw0_sys` y `fw0_sdfs`): la imagen nueva va a area temporal,
  se valida y solo entonces se activa. Un fallo de validacion deja la app vieja intacta.
- **OTA solo toca `fw0_sys` (app) y `fw0_sdfs` (recursos).** No puede tocar `mbrec` ni `recovery`.
  Peor caso realista: app no arranca -> `recovery` toma control -> re-push. Dificil de brickear de
  verdad por esta via.
- **Sin abrir = sin dump completo del NOR.** La red de seguridad es `recovery` + TEMP, no un backup
  byte-a-byte propio. La Ruta 2 (clip CH341A sobre el NOR) es la unica con backup total en tu mano.
- Backup posible por BLE: conservar los `.fw` stock (ya tenemos `zephyr.fw` = app). Para restaurar
  recursos habria que tener tambien el `.fw` de `sdfs` stock antes de tocarlo.

## 5. Puntos a confirmar en el scan live (pendiente, cuando conectes)

1. Presencia y handles reales de los servicios `e49a25f8` y `f48a23c0`.
2. MTU negociada (determina el tamano de trozo del stream).
3. Que emite el reloj por las TX notify durante idle y durante un intento de OTA (protocolo de flujo /
   PRN). Esto fija si el push es stream transparente o con framing file_tran (block-CRC 'I'/0xFF/'Z').
4. Si el modo OTA hay que dispararlo antes por el servicio vendor `f48a23c0` (comando TLV).
