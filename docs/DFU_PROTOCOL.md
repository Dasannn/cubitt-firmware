# Fase 3 - Protocolo DFU / OTA del Cubitt Viva Pro 2 (mapa desde binario + SDK)

> Nota de publicacion: registro historico de investigacion, con hipotesis pendientes.
> Los CRC observados no demuestran que el bootloader acepte firmware modificado.
> El mapa del SDK, la recuperacion ADFU y el flasheo completo no se han validado en el reloj.
> Las rutas a binarios, capturas y `scratchpad/` son referencias locales no distribuidas.
> Consulta el README para el alcance actual.

Fecha: 2026-07-06
Fuentes: decompilado Ghidra de `zephyr_image.bin` (funciones DFU/verify) + SDK
`ats3085s_dev_watch_ext_nor/firmware.xml`. Todo verificado, no supuesto.

## 1. Dos transportes de escritura

| Ruta | Medio | Funcion en binario | Recuperable | Backup completo |
|------|-------|--------------------|-------------|-----------------|
| ADFU | USB (mask-ROM) | `reboot adfu` + `adfus.bin` | Muy alta (ROM) | Si (read-back) |
| BLE DFU | GATT `file_tran_port_dfu` | `FUN_100cfe94` (parser) + `FUN_10123844` (log write_crc32) | Media (particion recovery) | Limitado |

Ambas escriben las MISMAS particiones con el MISMO formato de imagen (HTCA + CRC). BLE DFU no pasa
por la nube de Cubitt: empuja bloques directo por caracteristica GATT. ADFU es el mask-ROM del SoC.

## 2. Mapa de particiones (exacto, de firmware.xml del board que coincide)

Board = `ats3085s_dev_watch_ext_nor`. disk_size = 0x2000000 (32 MB NOR externo).

| addr | size | type | name | file | crc | enc | ota | dfu |
|------|------|------|------|------|-----|-----|-----|-----|
| 0x00000 | 0x1000 | BOOT | fw0_boot | mbrec.bin | no | no | no | si |
| 0x01000 | 0x1000 | SYS_PARAM | fw0_param | param.bin | no | no | no | si |
| 0x02000 | 0x1000 | BOOT | fw1_boot | (mirror de fw0_boot) | no | no | no | no |
| 0x03000 | 0x1000 | SYS_PARAM | fw1_param | (mirror) | no | no | no | no |
| 0x04000 | 0x30000 | RECOVERY | fw0_rec | recovery.bin | no | no | no | si |
| 0x34000 | 0x10000 | DATA | coredump | - | no | no | no | no |
| **0x44000** | **0x197000** | **SYSTEM** | **fw0_sys** | **app.bin** | no | **no** | **si** | si |
| **0x1db000** | **0x20000** | **DATA** | **fw0_sdfs** | **sdfs.bin** | no | **no** | **si** | si |
| 0x1fb000 | 0x1000 | DATA | nvram_factory | nvram.bin | no | no | no | si |
| 0x1fc000 | 0x2000 | DATA | nvram_factory_rw | - | no | no | no | no |
| 0x1fe000 | 0x2000 | DATA | nvram_user | - | no | no | no | no |

Conclusiones duras:
- **`enable_encryption=false` en TODAS.** Sin cifrado en flash. Confirma texto plano (entropia 7.08).
- **`enable_ota=true` solo en `fw0_sys` (app) y `fw0_sdfs` (recursos).** El OTA/BLE solo puede tocar
  esas dos. Bootloader (`mbrec`) y `recovery` NO se actualizan por OTA. Por eso `recovery` es el
  salvavidas si un OTA de app sale mal.
- El nombre interno del paquete OTA extraido es `zephyr.bin` = imagen que va a `fw0_sys` (app,
  load 0x10010000). Tamano app 1,252,000 B cabe en la particion de 0x197000 (1,667,072 B).
- Sin `<sign>` ni RSA en este XML. El board firmado (`ats3085s_dev_watch_sign`) es OTRO board. Este
  (el de Cubitt) es la variante no-sign.

## 3. Formato de item SDFS / nvram-region (NO es el wire BLE)

CORRECCION (2026-07-07): el formato `'I'/0xFF` de 8 bytes es el formato de **item del filesystem
SDFS** (nvram_region), tanto on-flash como dentro de la imagen `sdfs`. **No es el framing del
transporte BLE.** El "header" del item es el **nombre de archivo null-terminado**, y el "data" es el
contenido. Confirmado por DOS funciones independientes del firmware:

- Escritor: `FUN_10104f3c(ctx, name_ptr, data_ptr, data_len)` - construye el item y lo escribe a flash.
- Apply-reader: `FUN_101046b4` - recorre items staged y los copia (log `BUG: invalid nvram_region item`).
- Verify de item: `FUN_100cfe94(flash, offset, desc8, verify)` - lee de vuelta y checa CRC.

Cabecera de item de 8 bytes (verificada en el escritor `FUN_10104f3c`):

```
off 0 : 'I'  (0x49)              marca de item
off 1 : 0xFF                     tipo
off 2 : data_crc  (1 byte)       data_crc final: crc(data, crc(name+\0, crc(pkt[3:8],5,0)))
off 3 : head_crc  (1 byte)       head_crc(name+\0)  = (sum & 0xff) ^ 0xA5
off 4 : flag      (1 byte)       = 0 para items normales (entra en seed del data_crc)
off 5 : header_len (1 byte)      = strlen(name) + 1  (incluye el null terminador)
off 6 : data_len  (uint16 LE)    longitud del contenido; el escritor exige data_len <= 0x200
off 8+: [name + '\0' (header_len bytes)][data (data_len bytes)]
```

Secuencia exacta del escritor `FUN_10104f3c`:
```
*puVar1        = 0x0000ff49;                 // off0='I' off1=0xFF off2=0 off3=0
puVar1[1]      = 0;                          // off4..off7 = 0
bVar4          = strlen(name) + 1;
*(puVar1+5)    = bVar4;                       // off5 header_len
*(puVar1+3)    = head_crc(name, bVar4);       // off3
*(short)(puVar1+6) = data_len;                // off6-7
v = data_crc(puVar1+3, 5, 0);                 // seed sobre [off3,off4,off5,off6,off7]
v = data_crc(name, bVar4, v);                 // + nombre
*(puVar1+2) = data_crc(data, data_len, v);    // off2 final
// escribe [8B hdr][name+\0][data] a la sdfs (FUN_101051f4)
```
Stride del item en flash/imagen = `(header_len + data_len + 0x17) & align_mask`.

Codigos de retorno de `FUN_100cfe94`: `0`=skip/vacio, `1`=OK, `2`=fin (`'I''Z'`), `3`=error CRC.
El bloque de copia/lectura corre en trozos de **0x80 (128) bytes**. `write_crc32`/`read_crc32`
(`FUN_10123844`) solo emite traza `[file_tran_port_dfu]: write_crc32:%02x,read_crc32:%02x`.

Implicacion: para modificar un recurso en `sdfs` (p.ej. watch-face), se reconstruye la imagen `sdfs`
como secuencia de estos items (nombre+data+CRCs), luego se envuelve en la cabecera HTCA (seccion 4) y,
si va por OTA, en el contenedor 5A8778A5 (seccion 2). Todo reproducible con `crc_filetran.py`.

## 3c. Captura BLE en vivo (frida-gadget) - FUNCIONA

Via de captura del wire real (btsnoop muerto en MIUI): frida-gadget inyectado en la app
(`libapp.so` con `--add-needed libgadget.so` via LIEF; split arm64 re-firmado con `~/.android/debug.keystore`;
`install-multiple -p`). Gadget en modo Listen 127.0.0.1:27042. Hook de
`BluetoothGattCharacteristic.setValue` + `BluetoothGatt.writeCharacteristic` (overloads legacy y API33)
+ `onCharacteristicChanged`. Scripts en `scratchpad/`: `build_gadget.py`, `hook_ble.js`, `frida_run.py`.
Captura -> `scratchpad/ble_capture.log`.

Framing de transporte observado (servicio `0x0ff0`, write char `00000001` h.0x0025, notify `00000002` h.0x0027):

```
REQ (telefono->reloj):  c1 2b 01 01 01 13 | 76 00 | 00 00 00 | <payload protobuf...>
RESP/ACK (reloj->tel):  c1 ab 00 01 01 13 | 0b 00 | 00 00 00 | ad 20
```
- byte0 = `c1` magic de trama.
- byte1 = tipo/opcode (`0x2b` req; ACK = req | 0x80 = `0xab`).
- u16 LE de longitud (total de trama) hacia offset 6.
- payload = PROTOBUF (campos 08/10/18/20/2a...) para el sync de datos (notificaciones, ajustes).
- trailer `ad 20` = crc16 (en la RESP; a confirmar en REQ).

Esto es la capa de datos protobuf (sync). El file_tran/DFU crudo (items SDFS 'I'/0xFF de seccion 3)
va por el MISMO canal pero solo aparece al transferir un ARCHIVO (watch-face/recurso/firmware).
Pendiente: disparar una transferencia de archivo con la captura activa para grabar los comandos
file_tran (inicio/offset/prn/fin) y confirmar como se enmarca la imagen sdfs.

## 3b. Transporte BLE file_tran (protocol_file_tran) - capa aparte, PARCIAL

El wire BLE real (servicio `0000ff0`, write `0001`/notify `0002`) usa `protocol_file_tran`, una
transferencia resumible con negociacion: strings `get_offset_exec`, `prn:%d,file_name:%s`,
`length:%d,p_tran_request->file_name:%s`, `cur_tran_offset:%d`. Este framing de sesion (inicio,
offset, PRN=intervalo de notificacion, fin) es SEPARADO del formato de item SDFS de arriba y todavia
no esta reconstruido byte a byte. El codigo cliente que lo referencia no quedo desensamblado como
funcion en el proyecto Ghidra (refs por tabla de punteros de ops, no por flujo lineal). Ground truth
mas directo = captura BLE de un push real de watch-face desde la app, o hook del write en la app
(APK debuggable). Ver seccion 9.

## 4. Formato de cabecera de imagen HTCA (de `FUN_100f2218`, gate de boot/carga)

Cabecera de imagen de particion = **0x400 (1024) bytes**. Validacion antes de usar la imagen:

```
byte 0x00 : magic         == MAGIC (constante; si no coincide -> "wrong magic 0x%x")
byte 0x04 : header_crc32   CRC32 almacenado
byte 0x0A : header_size   (uint16) == 0x400  (si no -> "invalid header size %d")
byte 0x14 : image_size    <= 0x3000000 (48 MB)
byte 0x08..0x400 : cuerpo de cabecera cubierto por CRC
```

Verificacion: `crc32(header[0x08 : 0x08+0x3F8]) == header_crc32(0x04)`. Es CRC32 reflejado estandar
(`FUN_1011fdfc`, tabla nibble en `DAT_1011fe30`, init/final `~x`) = identico a `zlib.crc32`.
Si falla: `bad head crc`, imagen rechazada. **No hay comprobacion de firma/CMAC antes de aceptar.**

## 5. CRC en capas (todo el gate de integridad)

| Nivel | Que cubre | Funcion | Comparado contra |
|-------|-----------|---------|------------------|
| Contenedor OTA (5A8778A5) | payload completo | `zlib.crc32` | campo @0x0C |
| Cabecera de imagen HTCA | header[8:0x400] | `FUN_1011fdfc` (crc32) | header @0x04 |
| Item DFU (cabecera) | header_len bytes | `head_crc` `FUN_100ac3d4` | paquete off3 |
| Item DFU (datos) | off3..off7 + header + data | `data_crc` `FUN_100ac3ac` | paquete off2 |

Definiciones EXACTAS (decompiladas + bytes crudos del binario, ver `tools/repack/crc_filetran.py`):

- **head_crc** (`FUN_100ac3d4`, off3) = `(suma de header_bytes & 0xff) ^ 0xA5`. NO es CRC; checksum
  aditivo con XOR final 0xA5 (el mismo 0xA5 del magic 5A8778A5).
- **data_crc** (`FUN_100ac3ac`, off2) = checksum por **tabla de nibbles** de 32 bytes en `0x1011bb64`
  (file off 0x10bb64): `c = table[16+((c^b)>>4)] ^ table[(c^b)&0xf]` por byte, seed 0. Corre sobre
  `packet[3:8]` (off3,off4,off5,off6,off7) + header + todos los datos. **NO es un CRC lineal**
  (Tf[0]=0xB0); es una funcion propia del firmware. Tabla:
  `c0f300182de9fc41066804460a460027 708dc0f3c5018f4280f09080f06800eb`.

No hay ninguna capa criptografica (RSA/ECDSA/HMAC) en la ruta de imagen. Reempacar = recomputar
estos valores. Todos reproducibles y verificados en `py` (`crc_filetran.py` selftest OK).

## 6. AES-CMAC no es firma de imagen (confirmado en `FUN_100b389c`)

`FUN_100b389c` computa un CMAC de 8 bytes, invierte el orden de bytes y lo guarda como
**"Database Hash"** (`FUN_100b39d0`: "Failed to save Database Hash"). Es integridad de una base de
datos interna (app-data), NO del firmware. Strings: "Unable to setup AES CMAC",
"Unable to calculate hash". Fuera del gate de imagen. Confirma: el CMAC del binario no bloquea
flashear una imagen modificada.

## 7. Recuperacion (particion RECOVERY + flag_is_recovery_app)

`FUN_100f3b30` inicializa la imagen a escribir y lee bits del byte de flags del item:
- bit0: recovery app presente.
- `invalid flag_is_recovery_app` si el flag de recovery esta puesto sin bit0.
- Bloque de escritura de imagen = **0x800 (2048) bytes**. Storage detectado por nombre:
  `spi_flash` o `spinand` (`cannot found storage device %s`).

La particion `fw0_rec` (recovery.bin, 0x4000, 0x30000) es una mini-app que arranca si la app
principal queda corrupta. Es la red de seguridad de la ruta BLE. La red de seguridad de la ruta ADFU
es el propio mask-ROM (siempre recuperable).

## 8. Implicacion para Fase 6 (reempaque y flasheo)

Para producir una imagen `app`/recurso modificada aceptada por el reloj:
1. Modificar el contenido (recurso en `sdfs`/`bt_watch.res` primero; codigo despues).
2. Recalcular la cabecera HTCA (crc32 sobre `header[8:0x400]`, escribir en `0x04`; ajustar
   `image_size` en `0x14`).
3. Recalcular el CRC32 del contenedor 5A8778A5 (`zlib.crc32(payload)` en `0x0C`).
4. Si se empuja por BLE DFU: la app cliente arma los items con crc8 de cabecera y de datos por bloque;
   por ADFU se flashea la particion completa y el gate es la cabecera HTCA.
5. Flashear por **ADFU** (recuperable) para el primer ciclo. BLE OTA despues de validar.

Punto no observable en estatico: el `mbrec`/ROM on-device. Se cierra con dump ADFU (Fase 5)
comparando contra `bootloader/.../lark/bin/mbrec.bin` del SDK.

## Estado del gate de seguridad

CONFIRMADO en las cuatro capas: **integridad = CRC (crc8 por item + crc32 por imagen/contenedor),
sin firma criptografica.** Una imagen modificada con CRCs recomputados es aceptada por boot y por DFU.
Confianza ALTA. Ver `analysis/reports/fase1_signature_verdict.md` y `docs/PLATFORM_SDK.md`.
