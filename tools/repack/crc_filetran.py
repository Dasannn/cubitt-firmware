#!/usr/bin/env python3
"""
crc_filetran.py - Integrity functions for Cubitt Viva Pro 2 file_tran / file_tran_port_dfu.
Reproduction derived from firmware (zephyr_image.bin).

Source (decompilation and raw binary bytes):
  - head_crc = FUN_100ac3d4 @0x100ac3d4: sum of bytes & 0xff, then XOR 0xA5.
  - data_crc = FUN_100ac3ac @0x100ac3ac: nibble-table checksum with an initial seed,
               using a 32-byte table at 0x1011bb64 (file offset 0x10bb64).
               NOT a standard linear CRC (Tf[0]=0xB0); this is firmware-specific.

Use in the DFU parser (FUN_100cfe94), item packet ('I'+0xFF):
  off0='I' off1=0xFF off2=data_crc off3=head_crc off4=flag off5=hdr_len off6-7=data_len(LE)
  off8=[header (hdr_len)][data (data_len)]

  head_crc (off3) = head_crc(header_bytes)                  # sum^0xA5 over hdr_len bytes
  data_crc (off2) = data_crc(packet[3:8] + header + data, 0) # seed 0; includes off3..off7,
                   # then header, then ALL data bytes (firmware processes 0x80-byte
                   # chunks, but the result is the same as a single pass).
"""

# 32-byte table @0x1011bb64 (16 low-nibble + 16 high-nibble). Extracted from the binary.
_TABLE = bytes.fromhex(
    "c0f300182de9fc41066804460a460027"   # table[0..15]  (indexed by low nibble)
    "708dc0f3c5018f4280f09080f06800eb"   # table[16..31] (indexed by high nibble, +0x10)
)


def data_crc(data: bytes, seed: int = 0) -> int:
    """Exact FUN_100ac3ac: c = table[16 + ((c^b)>>4)] ^ table[(c^b)&0xf] per byte."""
    c = seed & 0xFF
    for b in data:
        x = (c ^ b) & 0xFF
        c = (_TABLE[16 + (x >> 4)] ^ _TABLE[x & 0x0F]) & 0xFF
    return c


def head_crc(data: bytes) -> int:
    """Exact FUN_100ac3d4: (sum of bytes & 0xff) ^ 0xA5."""
    s = 0
    for b in data:
        s = (s + b) & 0xFF
    return s ^ 0xA5


def dfu_item_crcs(header: bytes, data: bytes, flag: int = 0) -> dict:
    """
    Compute off2 (data_crc) and off3 (head_crc) for a DFU item from its header and data.
    Also return the 8-byte packet header, ready to prepend.
    """
    hlen = len(header)
    dlen = len(data)
    hc = head_crc(header)                              # off3
    # off2: seed 0 over [off3,off4,off5,off6,off7] + header + data
    pre = bytes([hc, flag & 0xFF, hlen & 0xFF, dlen & 0xFF, (dlen >> 8) & 0xFF])
    dc = data_crc(pre + header + data, 0)              # off2
    pkt_hdr = bytes([0x49, 0xFF, dc, hc, flag & 0xFF, hlen & 0xFF,
                     dlen & 0xFF, (dlen >> 8) & 0xFF])
    return {"data_crc": dc, "head_crc": hc, "packet_header": pkt_hdr}


# Fixed test vectors (matching the binary reproduction).
_TESTS_DATA = {
    (): 0x00, (0x00,): 0xB0, (0xFF,): 0xCC,
    (0x01, 0x02, 0x03): 0x82, (0x49, 0xFF, 0x00, 0x00, 0x00): 0xF6,
}
_TESTS_HEAD = {
    (): 0xA5, (0x00,): 0xA5, (0xFF,): 0x5A,
    (0x01, 0x02, 0x03): 0xA3, (0x49, 0xFF, 0x00, 0x00, 0x00): 0xED,
}


def _selftest():
    for v, exp in _TESTS_DATA.items():
        got = data_crc(bytes(v), 0)
        assert got == exp, f"data_crc{v}=0x{got:02x} != 0x{exp:02x}"
    for v, exp in _TESTS_HEAD.items():
        got = head_crc(bytes(v))
        assert got == exp, f"head_crc{v}=0x{got:02x} != 0x{exp:02x}"
    print("crc_filetran selftest OK")


if __name__ == "__main__":
    _selftest()
