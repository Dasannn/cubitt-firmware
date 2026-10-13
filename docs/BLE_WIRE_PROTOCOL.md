# Live BLE protocol (Cubitt / Creek) - captured with frida-gadget

> Publication note: historical research notes with unresolved hypotheses.
> Observed CRCs do not prove that the bootloader accepts modified firmware.
> The SDK map, ADFU recovery, and full flashing have not been validated on the watch.
> Binary, capture, and `scratchpad/` paths are local references not distributed here.
> See the README for the current scope.

Date: 2026-07-07. Source: actual app-to-watch capture through frida-gadget injected into `libapp.so`
(hooks on `BluetoothGattCharacteristic.setValue`, `BluetoothGatt.writeCharacteristic`, and
`onCharacteristicChanged`). GATT channel: service `0x0ff0`, write characteristic `00000001`
(h.0x0025), notify characteristic `00000002` (h.0x0027). The notes describe byte-level observations.

## 1. Transport frame

Fixed 11-byte header; protobuf payload; NOTIFY messages (watch-to-phone) append a 2-byte crc16.
Observed WRITE messages (phone-to-watch) do NOT carry that crc16 (length covers the entire frame).

```
off0     : 0xC1                 frame magic
off1     : seq (u8)             sequence number; INCREMENTS per request (0x27,0x28,...0x55...).
                                Response/notify sets bit7: response to seq N has off1 = N|0x80.
off2     : dir/flag             0x01 in phone-to-watch requests, 0x00 in watch-to-phone responses
off3     : 0x01                 version
off4-5   : channel/type (u16 LE) identifies the handler: 0x0016=files(list/info),
                                0x000e/0x010e=health, 0x0002, 0x0030, 0x0039, 0x003f=other syncs
off6-7   : length (u16 LE)      byte count = header(11) + payload (EXCLUDING the final crc16)
off8-10  : 00 00 00             reserved
off11+   : protobuf payload
[end]    : crc16 (2 bytes)      ONLY in watch-to-phone notifications (b3 3c, 1c 6f, ad 20, dd e2...)
```

CORRECTION: what was initially called an "opcode" (0x27/0x28/0x2b) was the SEQUENCE number,
not the type. Message type comes from the channel (off4-5) plus protobuf field f1.
Confirmed in sync after reconnecting (95 frames, sequential seq 0x27..0x55).
No application-level authentication/crypto handshake was observed: commands flowed directly over
the BLE bond, suggesting that a paired central, such as the PC, can issue commands without
additional authentication.

Raw examples:

```
REQ  file info    : c1 27 01 01 0016 2000 000000  08 01 12 11 "CWS05_8904_01.bin"
ACK               : c1 a7 00 01 0016 0b00 000000  b3 3c
REQ  list         : c1 28 01 01 0016 0d00 000000  08 00
RESP list (376B)  : c1 a8 00 01 0016 7601 000000  <directory protobuf>  1c 6f
```

## 2. Observed messages (initially labeled opcodes; see correction above)

| Sequence | ACK sequence | Meaning in this capture |
|---|---|---|
| 0x27 | 0xA7 | Get file information by name |
| 0x28 | 0xA8 | List the resource directory |
| 0x2B | 0xAB | Data sync (notifications, protobuf with app text) |
| 0x00 | 0x80 | Keepalive/status (payload 0803 1009...) |

GET/PUT data operations (transferring bytes of a .bin) had NOT yet been captured at this stage:
no file was transferred (watch faces were already on the watch; AGPS pushed no data during the
test). These were the next target; see section 5 for later findings.

## 3. Directory protobuf schema (captured response sequence 0xA8)

Top-level message:
- f3, f4, f5, f6, f8: directory counters/flags.
- f10 (repeated) = file entry:
  - f1 = category/partition (6=watch faces, 8, 2, 1).
  - f2 = index within the category.
  - f3 = **size in bytes** (always page-aligned: 0x40000, 0x68000, 0x110000...).
  - f4 = filename (`.bin`).
- f11 = total resource flash size (0x19f8000 ~= 26 MB).
- f12 = used/free (0x488000).
- f14 = active/selected file (`CWS05_8904_01.bin`).
- f15, f17 = flags.

## 4. Watch resource inventory (captured 2026-07-07)

| Category | Index | Size | Name |
|---|---|---|---|
| 6 | 6 | 0x68000 (425984) | 1G124compassCU@LC.bin |
| 6 | 4 | 0x90000 (589824) | 1G00119CUBT256N.bin |
| 6 | 2 | 0x78000 (491520) | 1G00122CUBT256N.bin |
| 6 | 3 | 0x60000 (393216) | 1G123compassCUBT.bin |
| 6 | 2 | 0x88000 (557056) | 1G00133CUBT256N.bin |
| 6 | 4 | 0x70000 (458752) | 1G00118CUBT256N.bin |
| 6 | 5 | 0x40000 (262144) | CWS05_8904_01.bin (ACTIVE) |
| 8 | 2 | 0x110000 (1114112) | 6G00016XCKJ2503U.bin |
| 2 | 6 | 0x48000 (294912) | CUB_C_WHF_25030303.bin |
| 1 | 3 | 0x28000 (163840) | CWS05_8906_05.bin |

These `.bin` files are `sdfs` resources (the named "items" in section 3 of DFU_PROTOCOL.md).
Item name = filename. The proposed modification workflow is GET the `.bin`, edit it, and PUT
it back; the complete workflow has not been validated.

## 4b. PC control tested (2026-07-07)

A PC running `bleak` (local script `scratchpad/ble_client.py`) connected to the watch
("Cubitt Viva Pro 2", MTU 500) and sent a manually constructed LIST frame:

```
WRITE char 0001: c1 01 01 01 00 16 0d 00 00 00 00 08 00
RESP notify 0002 (seq 0x81): complete directory (376B, same as through the app)
```

CONFIRMED observation: the PC, already paired over BLE, could use the watch's file protocol
directly, without the app or additional authentication. The original notes proposed this as
the basis for a future BLE PUT of a modified `.bin`; listing files does not validate flashing.
Services observed: `0ff0` (0001 write h37 / 0002 notify h39), `ffd0` (ffd1/ffd2/ffd3).

### Channel 0x16 subcommands (PC probing with a nonexistent filename)

Response = 13-byte frame `c1 [seq|80] 00 01 00 16 0b 00 00 00 [code] [crc16]`, code at off10.
- f1=0: LIST directory (returns the file protobuf).
- f1=1: select/open file by name -> code 0 if it exists (used by the app during every sync).
- f1=2: lookup -> code 3 (not found) for a nonexistent file.
- f1=3..9: code 0 (generic ACK / nonexistent subcommand, no observable effect).
- Verified: probing did NOT create or delete files (directory intact, 11 entries).
- No f1 returned BYTES with only `{f1,name}`. Data transfer was understood as a multi-step
  process (select -> get_offset -> blocks with offset+data). The offset/length/data fields had
  NOT been identified; attempting WRITES without a backup could be destructive, so that work stopped.

## 5. file_tran data protocol (PUT) - decoded from firmware (2026-07-07)

PUT does NOT use the channel 0x16 protobuf. Channel 0x16 (protobuf list/select/delete) is the
resource MANAGER. Byte transfer uses a raw binary subprotocol, `protocol_file_tran_client`
(Actions/Creek), handler `FUN_10097670` in the firmware (`middleware/protocol/protocol_file_tran/`).
The transport payload starts with command byte 0xD1..0xD4 (0xD5 falls through to default/no-op).
Verified through Ghidra decompilation.

Handler structure (state at `_DAT_10097934`, buffer at +0x0f, internal offsets):
- **0xD1 OPEN**: `[0xD1][...][off 0x0A: block_count][off 0x0B: file_name 64 bytes]`.
  Total payload length < 0x4c (76). Copies 64 name bytes, reads block_count, allocates a
  `block_count*0x100 + 0x100` buffer, and opens partitions (handler table `_DAT_10097938`,
  3 pointers per partition: [0]=open [1]=write [2]=finalize). Sets `cur_tran_offset` and `crc` to 0.
- **0xD2 DATA**: `[0xD2][idx] + data`. `len = payload_len - 2`; copies `len` bytes from `payload+2`
  into the buffer at `cur_offset` (state +0x15); increments a packet counter (+0x0a).
  When the counter reaches `block_count`, it flushes: calls the partition write handler
  (`_DAT_10097938[part*3+1]`), computes running **CRC32** (`FUN_100b2e84`, state +0x19), adds to
  the total offset (+0x1d), and resets the counter/buffer.
- **0xD3 STATUS/GET_OFFSET**: returns `crc` (+0x19) and total `cur_tran_offset` (+0x1d).
  Used to RESUME an interrupted transfer. Does not write; proposed as a read-only PC probe.
- **0xD4 COMMIT/END**: final flush and call to the finalize handler (`_DAT_10097938[part*3+2]`),
  then **compares accumulated CRC32 (+0x19) with `*(uint*)(payload+3)`** (4-byte CRC32 at offset 3
  of the commit message). Mismatch -> code 0x0b (error). Frees the buffer and resets
  (`FUN_10072470(state+7, 0x53)`). Actual flash writing uses SDFS 'I' items (FUN_10104f3c)
  through partition handlers.

Response: `func_0x10100fc8(&status_struct, code)`; the struct carries code + crc + offset
(which is why 0xD3/0xD4 return crc/offset to the phone). This maps to the app's Dart symbols:
`initFileSize`(0xD1) / `getOffset`(0xD3) / `writeFileDatas`(0xD2) / `commitChunk`+`getCrc`(0xD4).

**RESOLVED (live capture 2026-07-07):** file_tran uses NEITHER a separate channel NOR the C1
header. It uses the SAME GATT write characteristic `00000001` (notify `00000002`), but the written
value is the RAW 0xD1/0xD2/0xD4 PDU (no 0xC1 magic, no 11-byte header). This explains why channel
searches failed: the `first_byte==0xC1` filter discarded these frames. Captured by hooking
`BluetoothGattCharacteristic.setValue`/`writeCharacteristic` during an actual `phone.phone`
upload (triggered by editing a phone contact; the app recomputes the address book MD5 and
uploads it again through file_tran).

### Exact verified format (phone.phone upload, 17123 bytes)

```
OPEN   d1 00 [size LE u32] [size LE u32] [blocks_per_group u8] [ASCII name \0]
       example: d1 00 e3420000 e3420000 32  70686f6e652e70686f6e6500  ("phone.phone")
           size=0x42e3=17123 (x2: total and to-transfer), blocks_per_group=0x32=50
DATA   d2 [idx_u8] [up to 440 data bytes]
       idx = 0x00,0x01,... within the group (resets every 'blocks_per_group'); 39 frames,
       last frame shorter (403-byte payload). Sum of payloads = 17123 = exact size.
COMMIT d4 00 00 [crc32 LE u32]
       example: d4 00 00 ef400000 -> crc = 0x000040ef (FUN_100b2e84 over the file)
```

Notification responses on `00000002` (raw PDU, no C1):

```
d1 00 00   OPEN ack   (byte2 = code, 0=ok)
d4 00 00   COMMIT ack (0=ok; 0x0b on CRC mismatch)
```

The initial notes called a CRC rejection safe; because the handler flushes data before the
final comparison, this observation does not establish that all failed transfers leave flash intact.

D2 frames are not acknowledged individually (only D1 and D4 in the capture). This agrees with
firmware FUN_10097670: OPEN copies name (+0xb) and blk_count (+0xa), then allocates the buffer;
DATA accumulates by index and flushes/computes CRC32 every 'blocks_per_group'; COMMIT compares
the accumulated CRC against `*(u32*)(payload+3)`.

Raw artifact: `analysis/filetran_cap.txt`. Hooks: `scratchpad/hook_spp.js` + `hook_ble.js`.

### PUT from a PC (bleak) - proposed sequence

1. Connect over BLE, MTU >= ~450, start_notify on `00000002`.
2. Write OPEN to `00000001`; wait for `d1 00 00` notification.
3. Write each `d2 [idx] [<=440B]` block to `00000001` (idx resets every 50).
4. Write COMMIT `d4 00 00 [crc32]`; wait for `d4 00 00`.

The name includes a mount prefix depending on the port: watch faces = `/PTFS:/<file>.bin`
(seen in firmware logs as `data_open_handle:file_name=/PTFS:/CWS05_8906_05.bin`);
contacts = `phone.phone`; ephemerides = `ephemeris.agnss`/`ephemeris.gnss`; music = `music.track`.
Firmware ports: plate/agnss/gnss/track.

### CRC

- Commit CRC = CRC32 (`FUN_100b2e84`) over the file data, accumulated per block. Its exact
  polynomial/initialization must be reproduced to construct a valid COMMIT (extraction pending).
- Individual SDFS items also carry head_crc (FUN_100ac3d4) and data_crc (FUN_100ac3ac,
  nibble table @0x1011bb64), documented in DFU_PROTOCOL.md section 3.

## 5b. Watch-face source cached by the app (found 2026-07-07)

`/data/data/com.cubittpros.wear/app_flutter/dial/<MAC>/<dial>/firmware/` stores the watch face
as SOURCE: PNG layers (Hour/Min/Steps/Batarray/...), `dial.json` (manifest: frame_version,
dial_type, resolution_ratio, platform, element sn_list, preview), and the original downloaded
`.zip`. The app COMPILES this into `.bin` and pushes it through file_tran. Local copy in
`analysis/dial_source/`. The proposed workflow is to modify a PNG layer and reinstall so the
app recompiles and pushes it, avoiding manual `.bin` construction.
AGPS ephemerides are cached in `cache/{offLineEphemeris,realTimeLineEphemeris}/*.gnss|*.agnss`.

## Capture setup (original local workflow; scripts not included)

- `scratchpad/build_gadget.py`: repacks the arm64 split with the gadget (LIEF add-needed).
- `scratchpad/hook_ble.js`: write/notify hooks; logs to the PC and `/data/data/com.cubittpros.wear/files/ble_cap.log` (survives USB disconnects).
- Launch: `tail -f /dev/null | frida -H 127.0.0.1:27042 -n Gadget -l hook_ble.js -o ble_capture.log`
- Gadget: Listen mode at 127.0.0.1:27042, `adb forward tcp:27042 tcp:27042`.
