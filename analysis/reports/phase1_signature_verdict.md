# Phase 1 - Signature / secure boot verdict (preliminary, static)

> Publication note: historical research notes with unresolved hypotheses.
> Observed CRCs do not prove that the bootloader accepts modified firmware.
> The SDK map, ADFU recovery, and full flashing have not been validated on the watch.
> Binary, capture, and `scratchpad/` paths are local references not distributed here.
> See the README for the current scope.

Date: 2026-07-06
Goal: determine whether the Cubitt Viva Pro 2 OTA image is signed and whether this prevents
flashing a modified image.

## Files analyzed

- `analysis/firmware_candidates/zephyr.fw`: `5A8778A5` OTA container, 1,252,064 bytes.
- `analysis/firmware_candidates/zephyr_image.bin`: **corrected extraction** = `fw[0x40:]`,
  1,252,000 bytes, SHA256 `f27f23ad76b697ecdc5f9563fdb7016574a6b2fc283da664685732c6cd781606`.
  This is the executable image.
- `analysis/extracted/arm64/lib/arm64-v8a/libapp.so`: OTA client (Dart AOT).

Note: the earlier `zephyr.bin` was displaced by 0x200 (starting at the internal `ACTHHTCA`
subheader instead of the actual image start). The correct file is `zephyr_image.bin`.

## Confirmed container structure

Header = **0x40 bytes** (not 0x240). Layout:

| Offset | Bytes | Meaning |
|---|---|---|
| 0x00 | `5A 87 78 A5` | Container magic |
| 0x0C | `C8 AF 3B 67` | **Payload CRC32** (see below) |
| 0x10 | `A0 1A 13 00` | Payload length = 0x131AA0 = 1,252,000 |
| 0x14 | `A0 1A 13 00` | Length (duplicate) |
| 0x20 | `zephyr.bin\0` | Internal name |
| 0x40.. | Image | Cortex-M vector table + code (load 0x10010000) |

The 0x40-byte header contains no identified 16-byte CMAC or 256-byte RSA-2048 block.
It contains magic, CRC, length, and name fields.

## Key evidence and original interpretation

1. **CRC32 integrity identified.**
   `crc32(fw[0x40:]) = 0x673BAFC8` equals the field at `0x0C`, an exact match.
   The integrity field identified in the OTA package is a CRC32, which can be recomputed with
   `zlib.crc32` after a modification.

2. **Plaintext image.** Overall entropy 7.084 (mixed code/data, not encrypted).
   Valid ARM vector table at `payload[0]`: SP=0x01002140 (SRAM), reset=0x10075671
   (Thumb, inside the image). Load base 0x10010000.

3. **No appended signature identified.** Windowed entropy scan: maximum over 256 bytes = 7.56
   (normal compressed regions such as DSP/resources), with no isolated ~8.0 block identified
   as an RSA/ECDSA signature. The last 128 image bytes are pointer tables (entropy 3.1), not an
   identified MAC. Entropy alone cannot establish the absence of a signature.

4. **`AES CMAC` exists in code, but was not identified as image signing.** Reference string:
   "Unable to setup AES CMAC". The initial reasoning was that a required image CMAC would need
   to accompany the OTA package, whereas only CRC had been identified.

5. **Observed `efuse` references concern calibration.** Strings: "get efuse rf", "get efuse power",
   "get efuse avdd", associated with RF/power calibration. These references do not establish
   the absence of secure boot key fuses elsewhere.

6. **OTA client (libapp.so):** symbols `_checkNeedOta`, `checkUpgrade`, `ACTIVE_OTA_CHECK`,
   `check_firmware_upgrade`. The identified `hmac-sha256 ... signature=` use signs HTTP API
   requests (transport authentication), not firmware. RSA (PointyCastle) is bundled, but no
   obvious use was identified in the OTA flow.

## Original reasoning

The OTA package was understood to update **only the `app` partition** (`ACTHHTCA` subheader =
"app", load 0x10010000), carrying **only an identified CRC32**. The original analysis reasoned
that if the device bootloader required a per-image MAC/signature, a legitimate OTA would need
an updated signature, and therefore inferred that **there was no per-image cryptographic
check on the app partition**. This remains an inference from the available image, not proof
of the bootloader's complete behavior.

## Preliminary verdict

The original verdict strongly favored **CRC32 integrity without a cryptographic signature**,
and considered a modified `app` image with a recomputed CRC32 and repacked 0x40-byte header
likely to be accepted through DFU/boot.

Remaining uncertainty: the **device bootloader/mbrec is NOT in this file** (this is the app
loaded by that bootloader). The proposed ways to investigate whether a CMAC is checked before
jumping to the app were:
- Reverse engineering the verification path in Ghidra (Phase 3), or
- A complete flash dump through ADFU (Phase 5) to inspect mbrec/bootloader.

The original confidence was **medium-high** that signatures would not prevent reflashing
a modified app. Actual modified-image acceptance remains untested.

## Recommended next steps in the original plan

1. Phase 3 in Ghidra: load `zephyr_image.bin` at base 0x10010000, locate the app loader/jump,
   and inspect preceding CMAC/signature checks.
2. Phase 5 (requires the watch and its owner's authorization): obtain an ADFU dump to inspect
   the real bootloader and create a backup.

## Phase 3 (Ghidra) and Phase 2 (SDK) update - original verdict labeled CONFIRMED

Headless Ghidra (4655 functions, `zephyr_image.bin`) identified CRC checks in the inspected
update/loading paths:
- Per-block DFU: `[file_tran_port_dfu]: write_crc32:%02x` (FUN_10123844).
- Layered image/partition CRC validation: `bad head crc`, `bad data crc`,
  `invalid header crc 0x%x != hdr->crc 0x%x`, `item crc error`, `psn%d: crc check error`.
- `reboot adfu` / `reboot [adfu]` strings, originally interpreted as confirmation of ADFU recovery.
  Their presence does not validate recovery on the physical watch.
- Primitives present but not linked to image validation in this analysis: CRC32 tables
  (`0x10130930`, `0x1006d910`), AES sbox (`0x1006e4b4`), SHA256 K (`0x1011a1d8`), and AES-CMAC
  (FUN_100b389c), which computes an 8-byte hash/token for another use.

SDK (Phase 2): the Actions ATS3085 platform supports RSA signing as a **build option**
(`bootloader/boards/arm/ats3085s_dev_watch_sign`, `soc_rsa.c`). The original interpretation
was that Cubitt used the **unsigned** variant (CRC only).

The historical final verdict was **layered CRC integrity without signatures, HIGH confidence**.
Its proposed repacking procedure was to recompute ALL CRCs (container at 0x0C, header, data,
and items). The device mbrec/ROM remains outside the observed app image, requiring further
investigation through a device dump. See `docs/PLATFORM_SDK.md`.

**Current publication status:** the CRC observations are documented; acceptance of a modified
image by the actual bootloader and successful recovery have not been demonstrated.
