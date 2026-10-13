# Fase 2 - SDK de plataforma publico (fuente real)

> Nota de publicacion: registro historico de investigacion, con hipotesis pendientes.
> Los CRC observados no demuestran que el bootloader acepte firmware modificado.
> El mapa del SDK, la recuperacion ADFU y el flasheo completo no se han validado en el reloj.
> Las rutas a binarios, capturas y `scratchpad/` son referencias locales no distribuidas.
> Consulta el README para el alcance actual.

Fecha: 2026-07-06

## Identificacion del SoC/plataforma

Evidencia dentro de `zephyr_image.bin`:
- string `bt_watch` @0x68193 (aplicacion).
- string `lark` @0x8b50c (codename de board Actions ATS3085), `board` @0x88394.
- DSP core, algoritmos de salud (GH30x), BLE+RFCOMM dual, watch faces, SPI-NOR.

Conclusion: el Cubitt Viva Pro 2 usa un SoC **Actions ATS3085-series** (BT dual-mode smartwatch,
MCU+DSP), board familia **lark / ats3085x_dev_watch_ext_nor** (NOR externo SPI). Firmware = Zephyr
+ aplicacion `bt_watch` de Actions Technology.

## Fuente real localizada

Repo: **github.com/lvgl/lv_port_actions_technology** (branch `master`, ~330 MB, 17,007 archivos).
Contiene el arbol `action_technology_sdk/` = SDK Actions Technology basado en Zephyr. Es fuente real
compilable, no RE aproximado. Coincide 1:1 con el binario extraido.

Mapeo binario -> fuente:

| Elemento en el binario | Ruta en el SDK |
|------------------------|----------------|
| Aplicacion `bt_watch` | `action_technology_sdk/application/bt_watch/src/` |
| Bootloader / mbrec | `action_technology_sdk/bootloader/`, `bootloader/tools/prebuilt/lark/bin/mbrec.bin` |
| ADFU (recuperacion USB) | `bootloader/tools/prebuilt/lark/common/bin/adfus.bin`, `application/bt_watch/prebuild/ATT/att_adfu.bin` |
| Empaquetado .fw (contenedor/particiones) | `application/.../boards/ats3085*_dev_watch_ext_nor/firmware.xml` + `fwimage.cfg` |
| Watch faces / recursos (`bt_watch.res/.sty/.enG/.zhC`) | `application/.../boards/ats3085s_dev_watch_ext_nor/res/bt_watch.*` |
| SDFS (filesystem de recursos) + DSP | `application/.../boards/.../sdfs_k/` (incl. `adMUSIC.dsp`) |
| Crypto (AES/SHA/CMAC/RSA/ECDSA) | `thirdparty/crypto/mbedtls/`, `bootloader/soc/arm/actions/leopard/soc_rsa.c` |
| CRC de particion/imagen | `bootloader/include/partition/partition.h` |

## Implicacion para firma / secure-boot

El SDK trae una board de bootloader **con firma**: `bootloader/boards/arm/ats3085s_dev_watch_sign`
y `soc_rsa.c`. Es decir, **la firma RSA de imagen es una opcion de build de la plataforma**, no
obligatoria. La evidencia del binario de Cubitt (contenedor OTA con solo CRC32; ruta DFU
`file_tran_port_dfu` valida con `write_crc32`; validacion de particion por `hdr->crc`) indica que en
esta unidad **la firma NO esta activada**: se usa la variante no-sign (solo CRC).

Confirmacion 100% pendiente: leer el `mbrec`/bootloader real del reloj (dump ADFU, Fase 5) y
comparar contra la board `_sign` vs no-sign del SDK.

## Uso para ensenanza

- Leer `application/bt_watch/src/` da la arquitectura real (BLE, DFU, OTA, UI, sensores) que en el
  binario solo se ve como pseudo-C.
- `firmware.xml` + `fwimage.cfg` explican como se arma el `.fw` (contenedor 5A8778A5 + HTCA + tabla
  de particiones + CRCs). Es la receta para reempacar en Fase 6.
- ADFU (`adfus.bin`) + Actions Product Tool = via de flasheo/recuperacion.

## Caveat legal

Ninguno de los dos repos declara licencia explicita (GitHub: license = none). Para estudio personal
y clase es publico y accesible; redistribuir o derivar producto tiene limites legales
(codigo propiedad de Actions Technology, port publicado por LVGL). Tratar como referencia de estudio,
no como codigo con licencia abierta.

## Referencia secundaria

`github.com/ovsky/RE-ATS3603`: RE de Actions ATS3603 (handheld, no watch). Aporta `dump_mbrec.py` y
`decrypt.c`. Util como referencia de mbrec/ADFU, pero es otro SoC (ATS3603) y esas imagenes van
cifradas; la nuestra (ATS3085) esta en texto plano, asi que `decrypt.c` probablemente no aplica.
