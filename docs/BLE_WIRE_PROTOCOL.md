# Protocolo BLE en vivo (Cubitt / Creek) - capturado con frida-gadget

> Nota de publicacion: registro historico de investigacion, con hipotesis pendientes.
> Los CRC observados no demuestran que el bootloader acepte firmware modificado.
> El mapa del SDK, la recuperacion ADFU y el flasheo completo no se han validado en el reloj.
> Las rutas a binarios, capturas y `scratchpad/` son referencias locales no distribuidas.
> Consulta el README para el alcance actual.

Fecha: 2026-07-07. Fuente: captura real app->reloj via frida-gadget inyectado en `libapp.so`
(hook de `BluetoothGattCharacteristic.setValue` + `BluetoothGatt.writeCharacteristic` +
`onCharacteristicChanged`). Canal GATT: servicio `0x0ff0`, write char `00000001` (h.0x0025),
notify char `00000002` (h.0x0027). Todo verificado byte a byte, no supuesto.

## 1. Trama de transporte

Cabecera fija de 11 bytes; payload protobuf; las NOTIFY (reloj->telefono) anaden crc16 de 2 bytes
al final. Las WRITE (telefono->reloj) observadas NO llevan ese crc16 (la longitud cubre toda la trama).

```
off0     : 0xC1                 magic de trama
off1     : seq (u8)             numero de secuencia; INCREMENTA por request (0x27,0x28,...0x55...).
                                La respuesta/notify pone bit7: resp de seq N tiene off1 = N|0x80.
off2     : dir/flag             0x01 en req telefono->reloj, 0x00 en resp reloj->telefono
off3     : 0x01                 version
off4-5   : canal/tipo (u16 LE)  identifica el handler: 0x0016=archivos(list/info),
                                0x000e/0x010e=salud, 0x0002, 0x0030, 0x0039, 0x003f=otros syncs
off6-7   : length (u16 LE)      bytes contados = cabecera(11) + payload (SIN el crc16 final)
off8-10  : 00 00 00             reservado
off11+   : payload protobuf
[fin]    : crc16 (2 bytes)      SOLO en notify reloj->telefono (b3 3c, 1c 6f, ad 20, dd e2...)
```

CORRECCION: lo que antes llame "opcode" (0x27/0x28/0x2b) era el numero de SECUENCIA, no el tipo.
El tipo de mensaje lo da el canal (off4-5) + el campo f1 del protobuf. Confirmado en el sync tras
reconectar (95 frames, seq 0x27..0x55 secuencial). No se observo handshake de auth/crypto a nivel
app: los comandos fluyen directo sobre el bond BLE (implica que un central emparejado, p.ej. el PC,
puede emitir comandos sin auth extra).

Ejemplos crudos:
```
REQ  info archivo : c1 27 01 01 0016 2000 000000  08 01 12 11 "CWS05_8904_01.bin"
ACK               : c1 a7 00 01 0016 0b00 000000  b3 3c
REQ  lista        : c1 28 01 01 0016 0d00 000000  08 00
RESP lista (376B) : c1 a8 00 01 0016 7601 000000  <protobuf directorio>  1c 6f
```

## 2. Opcodes vistos
| opcode | ack | significado |
|--------|-----|-------------|
| 0x27 | 0xA7 | get info de un archivo (por nombre) |
| 0x28 | 0xA8 | listar directorio de recursos |
| 0x2B | 0xAB | sync de datos (notificaciones, protobuf con texto app) |
| 0x00 | 0x80 | keepalive/estado (payload 0803 1009...) |

Opcodes de datos GET/PUT (transferir bytes de un .bin) aun NO capturados: no se movio ningun
archivo (las caras ya estaban en el reloj; AGPS no empujo datos en la prueba). Son el siguiente
objetivo (ver seccion 5).

## 3. Esquema protobuf del directorio (opcode 0xA8)

Mensaje top-level:
- f3, f4, f5, f6, f8: contadores/flags del directorio.
- f10 (repetido) = entrada de archivo:
  - f1 = categoria/particion (6=caras, 8, 2, 1).
  - f2 = indice dentro de la categoria.
  - f3 = **tamano en bytes** (siempre alineado a pagina: 0x40000, 0x68000, 0x110000...).
  - f4 = nombre de archivo (`.bin`).
- f11 = tamano total de flash de recursos (0x19f8000 ~= 26 MB).
- f12 = usado/libre (0x488000).
- f14 = archivo activo/seleccionado (`CWS05_8904_01.bin`).
- f15, f17 = flags.

## 4. Inventario de recursos del reloj (capturado 2026-07-07)

| categoria | indice | tamano | nombre |
|-----------|--------|--------|--------|
| 6 | 6 | 0x68000 (425984) | 1G124compassCU@LC.bin |
| 6 | 4 | 0x90000 (589824) | 1G00119CUBT256N.bin |
| 6 | 2 | 0x78000 (491520) | 1G00122CUBT256N.bin |
| 6 | 3 | 0x60000 (393216) | 1G123compassCUBT.bin |
| 6 | 2 | 0x88000 (557056) | 1G00133CUBT256N.bin |
| 6 | 4 | 0x70000 (458752) | 1G00118CUBT256N.bin |
| 6 | 5 | 0x40000 (262144) | CWS05_8904_01.bin  (ACTIVA) |
| 8 | 2 | 0x110000 (1114112) | 6G00016XCKJ2503U.bin |
| 2 | 6 | 0x48000 (294912) | CUB_C_WHF_25030303.bin |
| 1 | 3 | 0x28000 (163840) | CWS05_8906_05.bin |

Estos `.bin` son los recursos del `sdfs` (los "items" nombrados de la seccion 3 de DFU_PROTOCOL.md).
El nombre del item = el nombre del archivo. Modificar una cara = GET del `.bin`, editar, PUT de vuelta.

## 4b. PC-driving PROBADO (2026-07-07)

Desde el PC con `bleak` (script `scratchpad/ble_client.py`) se conecto al reloj
("Cubitt Viva Pro 2", MTU 500) y se envio una trama LIST construida a mano:
```
WRITE char 0001: c1 01 01 01 00 16 0d 00 00 00 00 08 00
RESP notify 0002 (seq 0x81): directorio completo (376B, mismo que via app)
```
CONFIRMADO: el PC (ya emparejado por BLE) puede MANEJAR el protocolo de archivos del reloj
directamente, sin la app y sin auth extra. Esto es el mecanismo de flasheo por BLE (el PUT del `.bin`
modificado se hara igual, desde el PC). Servicios vistos: `0ff0` (0001 write h37 / 0002 notify h39),
`ffd0` (ffd1/ffd2/ffd3).

### Mapa de sub-comandos del canal 0x16 (sondeo seguro desde PC, nombre falso)
Respuesta = trama de 13 bytes `c1 [seq|80] 00 01 00 16 0b 00 00 00 [code] [crc16]`, code en off10.
- f1=0: LIST directorio (devuelve el protobuf de archivos).
- f1=1: seleccionar/abrir archivo por nombre -> code 0 si existe (lo usa la app en cada sync).
- f1=2: lookup -> code 3 (not found) para archivo inexistente.
- f1=3..9: code 0 (ack generico / sub-comando inexistente, sin efecto observable).
- Verificado: el sondeo NO creo ni borro archivos (directorio intacto, 11 entradas).
- Ningun f1 devolvio BYTES con solo `{f1,nombre}`. La transferencia de datos es multi-paso
  (seleccionar -> get_offset -> bloques con offset+data). Los campos offset/length/data NO estan
  identificados; probar ESCRITURA seria destructivo sin backup. Bloqueado por seguridad.

## 5. Protocolo de datos file_tran (PUT) - decodificado del firmware (2026-07-07)

El PUT NO va por el protobuf del canal 0x16. El canal 0x16 (protobuf list/select/delete) es el
MANAGER de recursos. La transferencia de bytes usa un sub-protocolo binario crudo, el
`protocol_file_tran_client` (Actions/Creek), handler `FUN_10097670` en el firmware
(`middleware/protocol/protocol_file_tran/`). El payload de la trama de transporte empieza con un
byte de comando 0xD1..0xD4 (0xD5 cae en default/no-op). Verificado por decompilacion en Ghidra.

Estructura del handler (estado en `_DAT_10097934`, buffer en +0x0f, offsets internos):
- **0xD1 OPEN**: `[0xD1][...][off 0x0A: block_count][off 0x0B: file_name 64 bytes]`. Longitud total
  del payload < 0x4c (76). Copia 64 bytes de nombre, lee block_count, aloca buffer `block_count*0x100
  + 0x100`, abre las particiones (tabla de handlers `_DAT_10097938`, 3 punteros por particion:
  [0]=open [1]=write [2]=finalize). Deja `cur_tran_offset` y `crc` en 0.
- **0xD2 DATA**: `[0xD2][idx] + data`. `len = payload_len - 2`; copia `len` bytes desde `payload+2`
  al buffer en la posicion `cur_offset` (estado +0x15); incrementa un contador de paquetes (+0x0a).
  Cuando el contador llega a `block_count`, hace flush: llama el handler write de la particion
  (`_DAT_10097938[part*3+1]`), computa **CRC32** corriente (`FUN_100b2e84`, estado +0x19), suma al
  offset total (+0x1d) y resetea el contador/buffer.
- **0xD3 STATUS/GET_OFFSET**: devuelve `crc` (+0x19) y `cur_tran_offset` total (+0x1d). Sirve para
  RESUME (retomar transferencia interrumpida). No escribe. Es el candidato de sondeo SEGURO desde PC.
- **0xD4 COMMIT/END**: flush final + llama el handler finalize (`_DAT_10097938[part*3+2]`), luego
  **compara el CRC32 acumulado (+0x19) contra `*(uint*)(payload+3)`** (CRC32 de 4 bytes en el offset 3
  del mensaje commit). Si no coincide -> code 0x0b (error). Libera el buffer y resetea (`FUN_10072470
  (state+7, 0x53)`). El escritor real a flash son los items SDFS 'I' (FUN_10104f3c) via los handlers
  de particion.

Respuesta: `func_0x10100fc8(&status_struct, code)`; la struct lleva el code + crc + offset (por eso
0xD3/0xD4 devuelven crc/offset al telefono). Mapea 1:1 a los symbols Dart de la app:
`initFileSize`(0xD1) / `getOffset`(0xD3) / `writeFileDatas`(0xD2) / `commitChunk`+`getCrc`(0xD4).

**RESUELTO (captura en vivo 2026-07-07):** el file_tran NO usa canal aparte NI el header C1. Va por la
MISMA caracteristica GATT de escritura `00000001` (notify `00000002`), pero el valor escrito es la PDU
CRUDA 0xD1/0xD2/0xD4 (sin magic 0xC1, sin cabecera de 11 bytes). Por eso las busquedas de canal
fallaban: el filtro `primer_byte==0xC1` descartaba justo estas tramas. Capturado hookeando
`BluetoothGattCharacteristic.setValue`/`writeCharacteristic` durante una subida real de `phone.phone`
(disparada editando un contacto del telefono; la app recomputa MD5 de la agenda y re-sube por file_tran).

### Formato exacto verificado (subida de phone.phone, 17123 bytes)
```
OPEN   d1 00 [size LE u32] [size LE u32] [blk_por_grupo u8] [nombre ASCII \0]
       ej: d1 00 e3420000 e3420000 32  70686f6e652e70686f6e6500  ("phone.phone")
           size=0x42e3=17123 (x2: total y a-transferir), blk_por_grupo=0x32=50
DATA   d2 [idx_u8] [hasta 440 bytes de datos]
       idx = 0x00,0x01,... dentro del grupo (se reinicia cada 'blk_por_grupo'); 39 tramas,
       ultima corta (payload 403). Suma de payloads = 17123 = size exacto.
COMMIT d4 00 00 [crc32 LE u32]
       ej: d4 00 00 ef400000  -> crc = 0x000040ef  (FUN_100b2e84 sobre el archivo)
```
Respuestas por notify en `00000002` (PDU cruda, sin C1):
```
d1 00 00   ack OPEN   (byte2 = code, 0=ok)
d4 00 00   ack COMMIT (0=ok; 0x0b si el CRC no cuadra -> rechazo SEGURO, no corrompe)
```
Las tramas D2 no se ack-ean una por una (solo D1 y D4 en la captura). Concuerda con firmware
FUN_10097670: OPEN copia nombre (+0xb) y blk_count (+0xa), aloca buffer; DATA acumula por idx y hace
flush+CRC32 cada 'blk_por_grupo'; COMMIT compara crc acumulado contra `*(u32*)(payload+3)`.

Artefacto crudo: `analysis/filetran_cap.txt`. Hook: `scratchpad/hook_spp.js` + `hook_ble.js`.

### PUT desde PC (bleak) - receta
1. Conectar BLE, MTU >= ~450, start_notify en `00000002`.
2. Escribir OPEN en `00000001`; esperar notify `d1 00 00`.
3. Escribir cada bloque `d2 [idx] [<=440B]` en `00000001` (idx reinicia cada 50).
4. Escribir COMMIT `d4 00 00 [crc32]`; esperar `d4 00 00`.
El nombre lleva prefijo de mount segun el puerto: caras = `/PTFS:/<archivo>.bin` (visto en logs de
firmware `data_open_handle:file_name=/PTFS:/CWS05_8906_05.bin`); contactos = `phone.phone`; efemerides
`ephemeris.agnss`/`ephemeris.gnss`; musica `music.track`. Ports firmware: plate/agnss/gnss/track.

### CRC
- Commit CRC = CRC32 (`FUN_100b2e84`) sobre los datos del archivo, acumulado por bloque. Hay que
  replicar su polinomio/init exactos para construir un COMMIT valido (pendiente extraer).
- Los items SDFS individuales llevan ademas head_crc (FUN_100ac3d4) y data_crc (FUN_100ac3ac,
  tabla nibble @0x1011bb64) documentados en DFU_PROTOCOL.md seccion 3.

## 5b. Fuente de caratulas cacheada por la app (hallado 2026-07-07)
`/data/data/com.cubittpros.wear/app_flutter/dial/<MAC>/<dial>/firmware/` guarda la caratula como
FUENTE: capas PNG (Hour/Min/Steps/Batarray/...), `dial.json` (manifest: frame_version, dial_type,
resolution_ratio, platform, sn_list de elementos, preview) y el `.zip` original descargado. La app
COMPILA esto al `.bin` y lo empuja por file_tran. Copia en `analysis/dial_source/`. Modificar una
capa PNG y reinstalar = la app recompila y empuja (no hace falta construir el `.bin` a mano).
Efemerides AGPS cacheadas en `cache/{offLineEphemeris,realTimeLineEphemeris}/*.gnss|*.agnss`.

## Setup de captura (reproducible)
- `scratchpad/build_gadget.py` : reempaqueta el split arm64 con el gadget (LIEF add-needed).
- `scratchpad/hook_ble.js` : hooks de write/notify; loguea a PC y a `/data/data/com.cubittpros.wear/files/ble_cap.log` (sobrevive caidas USB).
- Lanzar: `tail -f /dev/null | frida -H 127.0.0.1:27042 -n Gadget -l hook_ble.js -o ble_capture.log`
- Gadget: modo Listen 127.0.0.1:27042, `adb forward tcp:27042 tcp:27042`.
