# Phase 2 - Public platform SDK (actual source code)

> Publication note: historical research notes with unresolved hypotheses.
> Observed CRCs do not prove that the bootloader accepts modified firmware.
> The SDK map, ADFU recovery, and full flashing have not been validated on the watch.
> Binary, capture, and `scratchpad/` paths are local references not distributed here.
> See the README for the current scope.

Date: 2026-07-06

## SoC/platform identification

Evidence inside `zephyr_image.bin`:
- String `bt_watch` @0x68193 (application).
- String `lark` @0x8b50c (Actions ATS3085 board codename), `board` @0x88394.
- DSP core, health algorithms (GH30x), dual BLE+RFCOMM, watch faces, SPI-NOR.

Conclusion: the Cubitt Viva Pro 2 uses an **Actions ATS3085-series** SoC (dual-mode BT smartwatch,
MCU+DSP), **lark / ats3085x_dev_watch_ext_nor** board family (external SPI NOR). Firmware = Zephyr
+ Actions Technology's `bt_watch` application.

## Actual source located

Repository: **github.com/lvgl/lv_port_actions_technology** (`master` branch, ~330 MB, 17,007 files).
Contains the `action_technology_sdk/` tree: the Zephyr-based Actions Technology SDK. This is actual
buildable source, not an approximate reconstruction. The historical analysis reported a 1:1 match
with the extracted binary; see the publication note above for the limits of that conclusion.

Binary-to-source mapping:

| Binary element | SDK path |
|---|---|
| `bt_watch` application | `action_technology_sdk/application/bt_watch/src/` |
| Bootloader / mbrec | `action_technology_sdk/bootloader/`, `bootloader/tools/prebuilt/lark/bin/mbrec.bin` |
| ADFU (USB recovery) | `bootloader/tools/prebuilt/lark/common/bin/adfus.bin`, `application/bt_watch/prebuild/ATT/att_adfu.bin` |
| .fw packaging (container/partitions) | `application/.../boards/ats3085*_dev_watch_ext_nor/firmware.xml` + `fwimage.cfg` |
| Watch faces / resources (`bt_watch.res/.sty/.enG/.zhC`) | `application/.../boards/ats3085s_dev_watch_ext_nor/res/bt_watch.*` |
| SDFS (resource filesystem) + DSP | `application/.../boards/.../sdfs_k/` (including `adMUSIC.dsp`) |
| Crypto (AES/SHA/CMAC/RSA/ECDSA) | `thirdparty/crypto/mbedtls/`, `bootloader/soc/arm/actions/leopard/soc_rsa.c` |
| Partition/image CRC | `bootloader/include/partition/partition.h` |

## Implications for signatures / secure boot

The SDK includes a **signed** bootloader board: `bootloader/boards/arm/ats3085s_dev_watch_sign`
and `soc_rsa.c`. Thus, **RSA image signing is a platform build option**, not mandatory.
The Cubitt binary evidence (OTA container with CRC32 only; the `file_tran_port_dfu` DFU path
validating through `write_crc32`; partition validation through `hdr->crc`) was interpreted as
indicating that **signing is NOT enabled** on this unit: the unsigned variant uses CRC only.

Full confirmation is pending: read the watch's actual `mbrec`/bootloader (ADFU dump, Phase 5)
and compare it against the SDK's `_sign` and unsigned boards.

## Educational use

- Reading `application/bt_watch/src/` exposes the actual architecture (BLE, DFU, OTA, UI, sensors)
  that only appears as pseudo-C in the binary.
- `firmware.xml` + `fwimage.cfg` explain how the `.fw` is assembled (5A8778A5 container + HTCA +
  partition table + CRCs). This provides a repacking reference for Phase 6.
- ADFU (`adfus.bin`) + Actions Product Tool provide a platform flashing/recovery route.

## Third-party licensing

The original investigation recorded no explicit license for either reference repository
(GitHub: license = none). Public availability does not itself grant redistribution rights.
Treat the Actions Technology code and the LVGL-published port as study references; check their
own terms before reuse. The MIT license of this research repository does not relicense them.

## Secondary reference

`github.com/ovsky/RE-ATS3603`: reverse engineering of Actions ATS3603 (handheld, not a watch).
Provides `dump_mbrec.py` and `decrypt.c`. Useful as an mbrec/ADFU reference, but it concerns a
different SoC (ATS3603), and those images are encrypted. Our ATS3085 sample is plaintext,
so `decrypt.c` probably does not apply.
