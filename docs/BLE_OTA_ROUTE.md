# Route 1 - BLE flashing (without opening the watch) - GATT and protocol

> Publication note: historical research notes with unresolved hypotheses.
> Observed CRCs do not prove that the bootloader accepts modified firmware.
> The SDK map, ADFU recovery, and full flashing have not been validated on the watch.
> Binary, capture, and `scratchpad/` paths are local references not distributed here.
> See the README for the current scope.

Date: 2026-07-06
Sources: SDK `application/bt_watch/src/ota/ota_app_background.c`,
`application/bt_watch/src/vendor/vendor_app.c`, and bytes confirmed in
`analysis/firmware_candidates/zephyr_image.bin`. The original notes describe these as verified
in the binary rather than assumed; hardware conclusions remain subject to the note above.

## 1. GATT services exposed by the watch (identified in the binary)

Both GATT attribute tables are present in the firmware (128-bit UUIDs stored in reversed/LE order,
contiguous tables at 0x12f3xx-0x12f5xx in `zephyr_image.bin`).

### A. OTA service (flashing route) - from `ota_app_background.c`

| Role | UUID | Properties | Binary offset (LE) |
|---|---|---|---|
| Service | `e49a25f8-f69a-11e8-8eb2-f2801f1b9fd1` | Primary | 0x12f3a9 |
| RX (app-to-watch write) | `e49a25e0-f69a-11e8-8eb2-f2801f1b9fd1` | Write / WriteNoRsp | 0x12f419 |
| TX (watch-to-app notify) | `e49a28e1-f69a-11e8-8eb2-f2801f1b9fd1` | Notify | 0x12f4ad |
| CCC | `2902` (standard) | - | - |

This is the SDK's `ota_backend_bt` backend. It transports the **complete 5A8778A5 OTA container
as a transparent stream** to the watch; the watch's `ota_upgrade` module reads the container,
validates CRC32, writes it to the TEMP area, and reboots. There is also an SPP alias:
`00006666-0000-1000-8000-00805f9b34fb`.

### B. Vendor/data service (sync and OTA trigger) - from `vendor_app.c`

| Role | UUID | Properties | Binary offset (LE) |
|---|---|---|---|
| Service | `f48a23c0-f69a-11e8-8eb2-f2801f1b9fd1` | Primary | 0x12f539 |
| RX (write) | `f48a24c1-f69a-11e8-8eb2-f2801f1b9fd1` | Write / WriteNoRsp | 0x12f589 |
| TX (notify) | `f48a25c2-f69a-11e8-8eb2-f2801f1b9fd1` | Notify | 0x12f313 |
| CCC | `2902` | - | - |

Normal data channel (TLV: `tlv_pack(type, len, value)`). The app syncs through this channel and,
depending on the model, triggers OTA mode (`file_tran` / `protocol_file_tran`).

### Note about the Cubitt app

`libapp.so` (Dart AOT, flutter_blue_plus) only exposes the `00000ff0-...` service and a
`258eafa5-...` identifier as strings. The 128-bit UUIDs above are assembled from bytes at runtime,
which explains their absence as text.

### C. Actual GATT in normal mode (live scan 2026-07-06, anonymized address AA:BB:CC:DD:EE:FF)

Negotiated MTU = 23 (default). Present vendor services:

| Service | Char | Handle | Properties | Role |
|---|---|---|---|---|
| `00000ff0` | `00000001` | 0x0025 | write / wnr | **file_tran RX (DFU, app-to-watch)** |
| `00000ff0` | `00000002` | 0x0027 | notify | **file_tran TX (watch-to-app)** |
| `0000ffd0` | `0000ffd1` | 0x001c | write / wnr | vendor control write |
| `0000ffd0` | `0000ffd2` | 0x001e | notify | vendor control notify |
| `0000ffd0` | `0000ffd3` | 0x0021 | write / wnr / notify | vendor control rw |

Also present: 1800 (GAP), 1801 (GATT), 180a (DevInfo), 180d (HeartRate), 180f (Battery).

**The 128-bit OTA services `e49a25f8` and `f48a23c0` do NOT appear in normal mode.**
The historical interpretation was that they register only when the watch enters OTA mode
(triggered by the app, followed by a reboot / GATT table change). The working channel in normal
mode is therefore `00000ff0`. The original notes associated this with the `FUN_100cfe94` DFU
parser ('I'/0xFF/'Z', per-block crc8, 128-byte chunks); see the later SDFS/transport distinction
in `DFU_PROTOCOL.md` and `BLE_WIRE_PROTOCOL.md`.

Idle: no notification traffic for 25 seconds (the watch emitted only during sync/transfer).

## 2. 5A8778A5 OTA container (verified byte by byte)

Header: 0x40 bytes. Payload: raw app image loaded at 0x10010000 (Cortex-M vector table).

| Offset | Size | Field | Value in zephyr.fw |
|---|---|---|---|
| 0x00 | 4 | magic | `5A 87 78 A5` |
| 0x0C | 4 | **Payload CRC32 (zlib)** | `0x673bafc8` (verified) |
| 0x10 | 4 | payload length | `0x131aa0` = 1252000 |
| 0x14 | 4 | payload length (copy) | `0x131aa0` |
| 0x20 | 16 | name | `zephyr.bin` |
| 0x40 | .. | payload (app image) | @0x10010000 |

The integrity check identified in this container is **one CRC32 at 0x0C**, with no signature or
CMAC identified there. Repacking means modifying the payload and recomputing that CRC32
(and lengths if the size changes). See `tools/repack/repack_ota.py`.

## 3. End-to-end flow for Route 1 (research plan)

### Static phase (without the watch) - DONE / in progress

1. GATT UUIDs extracted (above).
2. Container packer available (`repack_ota.py`), CRC32 verified against the original.
3. `bleak` reconnaissance client available (`tools/ble/cubitt_ble_recon.py`).

### Reconnaissance phase (with the watch)

4. `cubitt_ble_recon.py` scans, connects, dumps the entire GATT table (services, characteristics,
   properties, handles, descriptors), and subscribes to TX notifications (`e49a28e1`, `f48a25c2`)
   to observe the watch. The original notes called this read-only; notification subscriptions
   configure the CCCD, but send no application data. This checks service presence, actual handles,
   and the negotiated MTU.

### Push phase (with the watch, WRITES - the original plan required explicit authorization per step)

5. Modify the payload (start with a minimal reversible change), then repack with `repack_ota.py`.
6. Subscribe to TX notifications, negotiate the MTU, and write the container in MTU-sized chunks
   to RX (`e49a25e0`), observing flow/PRN notifications from the watch.
7. Expected sequence: CRC32 validation -> write to TEMP -> reboot -> activate.
8. Check the display. The original recovery hypothesis was that TEMP preserves the current app,
   or the `recovery` partition boots if activation fails. This remains unvalidated on the watch.

## 4. Proposed recovery properties (not validated on this watch)

- **TEMP staging** (`ota_embed=TEMP` in `fw0_sys` and `fw0_sdfs`): the SDK model places the new
  image in a temporary area and validates it before activation. The expected behavior is to
  preserve the old app after a validation failure.
- **OTA targets `fw0_sys` (app) and `fw0_sdfs` (resources)** in the reference configuration,
  excluding `mbrec` and `recovery`. The original notes expected recovery to allow another push
  after an app boot failure. This does not establish protection against bricking the actual unit.
- **Without opening the watch, there is no complete NOR dump.** The proposed fallback is
  `recovery` + TEMP, not a personal byte-for-byte backup. Route 2 (CH341A clip on the NOR)
  was proposed for obtaining a complete backup.
- Potential BLE backup: preserve stock `.fw` files (`zephyr.fw` is the app sample). Restoring
  resources would also require the stock `sdfs` `.fw` before modifying them.

## 5. Points to confirm in a live scan (pending)

1. Presence and actual handles of `e49a25f8` and `f48a23c0`.
2. Negotiated MTU (determines stream chunk size).
3. TX notifications during idle and an OTA attempt (flow/PRN protocol), to determine whether
   the push is a transparent stream or uses file_tran framing. The initial 'I'/0xFF/'Z'
   interpretation was later revised; see the protocol documents.
4. Whether OTA mode must first be triggered through vendor service `f48a23c0` (TLV command).
