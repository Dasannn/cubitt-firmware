# Phase 3 - Cubitt Viva Pro 2 DFU / OTA protocol (binary and SDK mapping)

> Publication note: historical research notes with unresolved hypotheses.
> Observed CRCs do not prove that the bootloader accepts modified firmware.
> The SDK map, ADFU recovery, and full flashing have not been validated on the watch.
> Binary, capture, and `scratchpad/` paths are local references not distributed here.
> See the README for the current scope.

Date: 2026-07-06
Sources: Ghidra decompilation of `zephyr_image.bin` (DFU/verification functions) and SDK
`ats3085s_dev_watch_ext_nor/firmware.xml`. The original notes described the mapping as verified;
conclusions about the actual device remain subject to the publication note above.

## 1. Two write transports

| Route | Medium | Binary function | Recovery assessment in original notes | Full backup |
|---|---|---|---|---|
| ADFU | USB (mask ROM) | `reboot adfu` + `adfus.bin` | Very high (ROM) | Yes (read-back) |
| BLE DFU | GATT `file_tran_port_dfu` | `FUN_100cfe94` (parser) + `FUN_10123844` (write_crc32 log) | Medium (recovery partition) | Limited |

The analysis associated both routes with the SAME partitions and image format (HTCA + CRC).
BLE DFU sends blocks directly through a GATT characteristic, without Cubitt's cloud.
ADFU is associated with the SoC's mask ROM. Device recovery and read-back remain unvalidated.

## 2. Partition map (from firmware.xml of the reference board)

Board = `ats3085s_dev_watch_ext_nor`. disk_size = 0x2000000 (32 MB external NOR).

| addr | size | type | name | file | crc | enc | ota | dfu |
|---|---|---|---|---|---|---|---|---|
| 0x00000 | 0x1000 | BOOT | fw0_boot | mbrec.bin | no | no | no | yes |
| 0x01000 | 0x1000 | SYS_PARAM | fw0_param | param.bin | no | no | no | yes |
| 0x02000 | 0x1000 | BOOT | fw1_boot | (mirror of fw0_boot) | no | no | no | no |
| 0x03000 | 0x1000 | SYS_PARAM | fw1_param | (mirror) | no | no | no | no |
| 0x04000 | 0x30000 | RECOVERY | fw0_rec | recovery.bin | no | no | no | yes |
| 0x34000 | 0x10000 | DATA | coredump | - | no | no | no | no |
| **0x44000** | **0x197000** | **SYSTEM** | **fw0_sys** | **app.bin** | no | **no** | **yes** | yes |
| **0x1db000** | **0x20000** | **DATA** | **fw0_sdfs** | **sdfs.bin** | no | **no** | **yes** | yes |
| 0x1fb000 | 0x1000 | DATA | nvram_factory | nvram.bin | no | no | no | yes |
| 0x1fc000 | 0x2000 | DATA | nvram_factory_rw | - | no | no | no | no |
| 0x1fe000 | 0x2000 | DATA | nvram_user | - | no | no | no | no |

Original conclusions from this configuration:
- **`enable_encryption=false` for ALL partitions.** No flash encryption in this configuration,
  consistent with the plaintext sample (entropy 7.08).
- **`enable_ota=true` only for `fw0_sys` (app) and `fw0_sdfs` (resources).** OTA/BLE would target
  only these two. Bootloader (`mbrec`) and `recovery` are NOT updated through OTA in this map.
  The proposed fallback after an app OTA failure was the `recovery` partition.
- The extracted OTA package's internal name is `zephyr.bin`, associated with `fw0_sys`
  (app, load 0x10010000). The 1,252,000-byte app fits the 0x197000-byte (1,667,072-byte) partition.
- No `<sign>` or RSA in this XML. The signed board (`ats3085s_dev_watch_sign`) is a DIFFERENT
  board. The original analysis inferred that Cubitt used the unsigned variant; confirmation
  requires the actual device bootloader.

## 3. SDFS / nvram-region item format (NOT the BLE wire format)

CORRECTION (2026-07-07): the 8-byte `'I'/0xFF` format is the **SDFS filesystem item format**
(nvram_region), both on flash and inside the `sdfs` image. **It is not BLE transport framing.**
The item "header" is the **null-terminated filename**, and "data" is its contents.
Confirmed through TWO independent firmware functions:

- Writer: `FUN_10104f3c(ctx, name_ptr, data_ptr, data_len)` builds the item and writes it to flash.
- Apply-reader: `FUN_101046b4` iterates staged items and copies them (log: `BUG: invalid nvram_region item`).
- Item verifier: `FUN_100cfe94(flash, offset, desc8, verify)` reads back and checks CRC.

8-byte item header (verified in writer `FUN_10104f3c`):

```
off 0 : 'I'  (0x49)              item marker
off 1 : 0xFF                     type
off 2 : data_crc  (1 byte)       final data_crc: crc(data, crc(name+\0, crc(pkt[3:8],5,0)))
off 3 : head_crc  (1 byte)       head_crc(name+\0) = (sum & 0xff) ^ 0xA5
off 4 : flag      (1 byte)       = 0 for normal items (included in the data_crc seed input)
off 5 : header_len (1 byte)      = strlen(name) + 1 (includes the null terminator)
off 6 : data_len  (uint16 LE)    content length; the writer requires data_len <= 0x200
off 8+: [name + '\0' (header_len bytes)][data (data_len bytes)]
```

Exact writer sequence in `FUN_10104f3c`:

```
*puVar1        = 0x0000ff49;                 // off0='I' off1=0xFF off2=0 off3=0
puVar1[1]      = 0;                          // off4..off7 = 0
bVar4          = strlen(name) + 1;
*(puVar1+5)    = bVar4;                       // off5 header_len
*(puVar1+3)    = head_crc(name, bVar4);       // off3
*(short)(puVar1+6) = data_len;                // off6-7
v = data_crc(puVar1+3, 5, 0);                 // seed over [off3,off4,off5,off6,off7]
v = data_crc(name, bVar4, v);                 // + name
*(puVar1+2) = data_crc(data, data_len, v);    // final off2
// write [8B hdr][name+\0][data] to sdfs (FUN_101051f4)
```

Item stride in flash/image = `(header_len + data_len + 0x17) & align_mask`.

`FUN_100cfe94` return codes: `0`=skip/empty, `1`=OK, `2`=end (`'I''Z'`), `3`=CRC error.
The copy/read block runs in **0x80-byte (128-byte) chunks**. `write_crc32`/`read_crc32`
(`FUN_10123844`) only emits `[file_tran_port_dfu]: write_crc32:%02x,read_crc32:%02x` traces.

Implication: to modify an `sdfs` resource (e.g. a watch face), reconstruct the `sdfs` image
as a sequence of these items (name+data+CRCs), then wrap it in the HTCA header (section 4) and,
for OTA, the 5A8778A5 container (see `BLE_OTA_ROUTE.md`, section 2). The checksum reproduction
is available in `crc_filetran.py`.

## 3c. Live BLE capture (frida-gadget) - working in the original investigation

Capture method for the actual wire traffic (btsnoop was unavailable on MIUI): frida-gadget
injected into the app (`libapp.so` with `--add-needed libgadget.so` through LIEF; arm64 split
re-signed with `~/.android/debug.keystore`; `install-multiple -p`). Gadget in Listen mode at
127.0.0.1:27042. Hooks on `BluetoothGattCharacteristic.setValue` and
`BluetoothGatt.writeCharacteristic` (legacy and API33 overloads), plus `onCharacteristicChanged`.
Local scripts in `scratchpad/`: `build_gadget.py`, `hook_ble.js`, `frida_run.py`.
Capture output: `scratchpad/ble_capture.log`.

Observed transport framing (service `0x0ff0`, write char `00000001` h.0x0025, notify `00000002` h.0x0027):

```
REQ (phone->watch):  c1 2b 01 01 01 13 | 76 00 | 00 00 00 | <protobuf payload...>
RESP/ACK (watch->phone): c1 ab 00 01 01 13 | 0b 00 | 00 00 00 | ad 20
```

Initial interpretation (later corrections are in `BLE_WIRE_PROTOCOL.md`):
- byte0 = `c1` frame magic.
- byte1 = type/opcode (`0x2b` request; ACK = request | 0x80 = `0xab`).
- u16 LE length (total frame) near offset 6.
- Payload = PROTOBUF (fields 08/10/18/20/2a...) for data sync (notifications, settings).
- Trailer `ad 20` = crc16 (in the response; request still needed confirmation).

This is the protobuf data layer (sync). The original notes associated raw file_tran/DFU with
SDFS 'I'/0xFF items from section 3 on the SAME channel, appearing only during FILE transfers
(watch face/resource/firmware). The later capture distinguishes raw D1-D4 PDUs from SDFS items.
At this stage, capturing a file transfer was pending to record file_tran commands
(start/offset/PRN/end) and establish how the sdfs image was framed.

## 3b. BLE file_tran transport (protocol_file_tran) - separate layer, PARTIAL

The actual BLE wire protocol (service `0000ff0`, write `0001` / notify `0002`) uses
`protocol_file_tran`, a resumable transfer with negotiation: strings `get_offset_exec`,
`prn:%d,file_name:%s`, `length:%d,p_tran_request->file_name:%s`, `cur_tran_offset:%d`.
This session framing (start, offset, PRN=notification interval, end) is SEPARATE from the SDFS
item format above and had not yet been reconstructed byte by byte at this stage.
The referencing client code was not disassembled as a function in the Ghidra project
(references through an operations pointer table, not linear flow). The most direct evidence
would be a BLE capture of an actual watch-face push from the app, or a write hook in a debuggable
APK. See the later findings in `BLE_WIRE_PROTOCOL.md`.

## 4. HTCA image header format (from `FUN_100f2218`, boot/load validation)

Partition image header = **0x400 (1024) bytes**. Validation before using the image:

```
byte 0x00 : magic         == MAGIC (constant; mismatch -> "wrong magic 0x%x")
byte 0x04 : header_crc32   stored CRC32
byte 0x0A : header_size   (uint16) == 0x400 (otherwise -> "invalid header size %d")
byte 0x14 : image_size    <= 0x3000000 (48 MB)
byte 0x08..0x400 : header body covered by CRC
```

Verification: `crc32(header[0x08 : 0x08+0x3F8]) == header_crc32(0x04)`.
Standard reflected CRC32 (`FUN_1011fdfc`, nibble table at `DAT_1011fe30`, init/final `~x`),
identical to `zlib.crc32`. On failure: `bad head crc`, image rejected.
The original analysis identified no signature/CMAC check in this path; that does not establish
what the separate device bootloader enforces.

## 5. CRC layers (identified integrity checks)

| Level | Coverage | Function | Compared against |
|---|---|---|---|
| OTA container (5A8778A5) | Entire payload | `zlib.crc32` | Field @0x0C |
| HTCA image header | header[8:0x400] | `FUN_1011fdfc` (crc32) | Header @0x04 |
| DFU item (header) | header_len bytes | `head_crc` `FUN_100ac3d4` | Packet off3 |
| DFU item (data) | off3..off7 + header + data | `data_crc` `FUN_100ac3ac` | Packet off2 |

Definitions from decompilation and raw binary bytes (see `tools/repack/crc_filetran.py`):

- **head_crc** (`FUN_100ac3d4`, off3) = `(sum of header_bytes & 0xff) ^ 0xA5`. NOT a CRC;
  an additive checksum with a final XOR of 0xA5 (the same 0xA5 as in magic 5A8778A5).
- **data_crc** (`FUN_100ac3ac`, off2) = checksum using a **32-byte nibble table** at `0x1011bb64`
  (file offset 0x10bb64): `c = table[16+((c^b)>>4)] ^ table[(c^b)&0xf]` per byte, seed 0.
  Runs over `packet[3:8]` (off3,off4,off5,off6,off7) + header + all data. **NOT a linear CRC**
  (Tf[0]=0xB0); it is a firmware-specific function. Table:
  `c0f300182de9fc41066804460a460027 708dc0f3c5018f4280f09080f06800eb`.

The original analysis found no cryptographic layer (RSA/ECDSA/HMAC) in the inspected image path.
Repacking requires recomputing these values. Local Python reproduction passed
(`crc_filetran.py` self-test OK).

## 6. AES-CMAC use identified in `FUN_100b389c`

`FUN_100b389c` computes an 8-byte CMAC, reverses the byte order, and stores it as
**"Database Hash"** (`FUN_100b39d0`: "Failed to save Database Hash"). The investigation interpreted
this as internal database integrity (app data), NOT firmware integrity. Strings:
"Unable to setup AES CMAC", "Unable to calculate hash". This function was considered outside
image validation; its presence alone neither proves nor disproves bootloader signature checks.

## 7. Recovery (RECOVERY partition and flag_is_recovery_app)

`FUN_100f3b30` initializes the image to write and reads bits from the item's flags byte:
- bit0: recovery app present.
- `invalid flag_is_recovery_app` if the recovery flag is set without bit0.
- Image write block = **0x800 (2048) bytes**. Storage detected by name:
  `spi_flash` or `spinand` (`cannot found storage device %s`).

The original interpretation was that `fw0_rec` (recovery.bin, 0x4000, 0x30000) is a small app
that boots if the main app is corrupt, providing the BLE fallback, while mask ROM provides
the ADFU fallback. Neither recovery path has been validated on this watch.

## 8. Implications for Phase 6 (repacking and flashing research)

Proposed steps for producing a modified `app`/resource image:

1. Modify the contents (an `sdfs`/`bt_watch.res` resource first, code later).
2. Recalculate the HTCA header (crc32 over `header[8:0x400]`, write at `0x04`; adjust
   `image_size` at `0x14`).
3. Recalculate the 5A8778A5 container CRC32 (`zlib.crc32(payload)` at `0x0C`).
4. For BLE DFU, the client assembles items with header and per-block data checksums;
   for ADFU, the complete partition is flashed with HTCA header validation.
5. The original plan proposed **ADFU** for the first cycle, then BLE OTA after validation.
   This remains a research plan, not a validated installation procedure.

The device's `mbrec`/ROM cannot be established from this app image alone. The proposed next
step is an ADFU dump (Phase 5), compared against the SDK's `bootloader/.../lark/bin/mbrec.bin`.

## Security validation status

The original notes concluded, with high confidence, that all four layers used CRC
(per-item crc8 and per-image/container crc32) without a cryptographic signature, and inferred
that modified images would be accepted. **That inference is not a hardware acceptance test.**
See `analysis/reports/phase1_signature_verdict.md` and `docs/PLATFORM_SDK.md`.
