#!/usr/bin/env python3
"""
repack_ota.py - Repack the Cubitt Viva Pro 2 5A8778A5 OTA container.

Container format (checked byte by byte against analysis/firmware_candidates/zephyr.fw):
  0x00  4  magic          5A 87 78 A5
  0x0C  4  crc32(payload) zlib.crc32 over the payload starting at file offset 0x40
  0x10  4  payload length LE u32
  0x14  4  payload length LE u32 (copy)
  0x20 16  name           "zephyr.bin"
  0x40  .. payload        raw app image @0x10010000

Repacking patches the payload and recomputes the container CRC32.
This does not establish whether the device bootloader accepts modified images.

Usage:
  # Check that a .fw has the correct CRC32:
  python repack_ota.py verify  zephyr.fw

  # Extract the payload (app image) to a file for editing:
  python repack_ota.py extract zephyr.fw payload.bin

  # Rebuild the container from a possibly modified payload:
  python repack_ota.py build   zephyr.fw payload.bin zephyr_mod.fw

  # Patch N bytes at a payload offset and rebuild without changing size:
  python repack_ota.py patch   zephyr.fw <off_hex> <hexbytes> zephyr_mod.fw
"""
import sys, zlib, struct

MAGIC = bytes.fromhex("5a8778a5")
HDR_LEN = 0x40
OFF_MAGIC = 0x00
OFF_CRC32 = 0x0C
OFF_LEN1  = 0x10
OFF_LEN2  = 0x14


def parse(fw: bytes):
    if fw[OFF_MAGIC:OFF_MAGIC+4] != MAGIC:
        raise SystemExit(f"invalid magic: {fw[:4].hex()} (expected 5a8778a5)")
    stored_crc = struct.unpack_from("<I", fw, OFF_CRC32)[0]
    len1 = struct.unpack_from("<I", fw, OFF_LEN1)[0]
    len2 = struct.unpack_from("<I", fw, OFF_LEN2)[0]
    payload = fw[HDR_LEN:]
    return stored_crc, len1, len2, payload


def calc_crc(payload: bytes) -> int:
    return zlib.crc32(payload) & 0xFFFFFFFF


def cmd_verify(path):
    fw = open(path, "rb").read()
    stored, len1, len2, payload = parse(fw)
    calc = calc_crc(payload)
    print(f"file            : {path}")
    print(f"container size  : {len(fw)}")
    print(f"header          : 0x{HDR_LEN:x}")
    print(f"payload len     : {len(payload)}  (field@0x10={len1}, @0x14={len2})")
    print(f"stored crc32    : 0x{stored:08x}")
    print(f"computed crc32  : 0x{calc:08x}")
    ok = (calc == stored) and (len1 == len(payload) == len2)
    print("VERIFIED OK" if ok else "MISMATCH")
    return 0 if ok else 1


def cmd_extract(path, out):
    fw = open(path, "rb").read()
    _, _, _, payload = parse(fw)
    open(out, "wb").write(payload)
    print(f"payload {len(payload)} bytes -> {out}")


def build(fw_template: bytes, payload: bytes) -> bytes:
    out = bytearray(fw_template[:HDR_LEN])          # preserve original header
    struct.pack_into("<I", out, OFF_CRC32, calc_crc(payload))
    struct.pack_into("<I", out, OFF_LEN1, len(payload))
    struct.pack_into("<I", out, OFF_LEN2, len(payload))
    out += payload
    return bytes(out)


def cmd_build(template_path, payload_path, out_path):
    fw = open(template_path, "rb").read()
    payload = open(payload_path, "rb").read()
    orig_len = len(fw) - HDR_LEN
    if len(payload) != orig_len:
        print(f"WARNING: payload {len(payload)} != original {orig_len}. "
              f"Changing the size may overflow the fw0_sys partition (0x197000). "
              f"Continuing, but check the limit.")
    out = build(fw, payload)
    open(out_path, "wb").write(out)
    stored, _, _, p = parse(out)
    print(f"written {out_path}  ({len(out)} bytes)  crc32=0x{stored:08x}  "
          f"(recheck {'OK' if calc_crc(p)==stored else 'FAIL'})")


def cmd_patch(template_path, off_hex, hexbytes, out_path):
    fw = open(template_path, "rb").read()
    _, _, _, payload = parse(fw)
    payload = bytearray(payload)
    off = int(off_hex, 16) if off_hex.lower().startswith("0x") else int(off_hex, 16)
    patch = bytes.fromhex(hexbytes)
    if off + len(patch) > len(payload):
        raise SystemExit(f"patch out of range: 0x{off:x}+{len(patch)} > {len(payload)}")
    before = bytes(payload[off:off+len(patch)])
    payload[off:off+len(patch)] = patch
    out = build(fw, bytes(payload))
    open(out_path, "wb").write(out)
    print(f"patch @0x{off:x}: {before.hex()} -> {patch.hex()}")
    stored, _, _, p = parse(out)
    print(f"written {out_path}  crc32=0x{stored:08x}  "
          f"(recheck {'OK' if calc_crc(p)==stored else 'FAIL'})")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 1
    c = a[0]
    if c == "verify"  and len(a) == 2: return cmd_verify(a[1])
    if c == "extract" and len(a) == 3: return cmd_extract(a[1], a[2])
    if c == "build"   and len(a) == 4: return cmd_build(a[1], a[2], a[3])
    if c == "patch"   and len(a) == 5: return cmd_patch(a[1], a[2], a[3], a[4])
    print(__doc__); return 1


if __name__ == "__main__":
    raise SystemExit(main())
