#!/usr/bin/env python3
"""
cubitt_ble_recon.py - GATT reconnaissance for Cubitt Viva Pro 2.

What it does:
  1. Scan BLE and list devices (optional name filter).
  2. Connect to the watch.
  3. Dump the ENTIRE GATT table: services, characteristics, properties, handles, descriptors.
  4. Mark whether OTA (e49a25f8) and vendor (f48a23c0) services are present.
  5. Subscribe to TX notifications and record watch output for <observe> seconds.
  Sends NO application data and does NOT trigger OTA.
  Notification subscriptions configure the CCCD; --observe 0 disables subscriptions.

Requirements:
  pip install bleak
  Bluetooth LE enabled on the PC.

Usage:
  python cubitt_ble_recon.py --scan                 # list devices only
  python cubitt_ble_recon.py --name Cubitt          # connect by name and dump GATT
  python cubitt_ble_recon.py --addr AA:BB:CC:DD:EE:FF --observe 30
"""
import argparse, asyncio, sys

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    sys.exit("Missing bleak. Install: pip install bleak")

# --- 128-bit services associated with OTA mode (absent in normal-mode scan) ---
OTA_SVC    = "e49a25f8-f69a-11e8-8eb2-f2801f1b9fd1"
OTA_RX     = "e49a25e0-f69a-11e8-8eb2-f2801f1b9fd1"
OTA_TX     = "e49a28e1-f69a-11e8-8eb2-f2801f1b9fd1"
VENDOR_SVC = "f48a23c0-f69a-11e8-8eb2-f2801f1b9fd1"
VENDOR_RX  = "f48a24c1-f69a-11e8-8eb2-f2801f1b9fd1"
VENDOR_TX  = "f48a25c2-f69a-11e8-8eb2-f2801f1b9fd1"
# --- actual channels confirmed in normal mode (live scan 2026-07-06) ---
PF_SVC = "00000ff0-0000-1000-8000-00805f9b34fb"   # protocol_ble / file_tran (actual DFU)
PF_RX  = "00000001-0000-1000-8000-00805f9b34fb"   # write   (app -> watch)  handle 0x0025
PF_TX  = "00000002-0000-1000-8000-00805f9b34fb"   # notify  (watch -> app)  handle 0x0027
VD_SVC = "0000ffd0-0000-1000-8000-00805f9b34fb"   # vendor control
VD_W   = "0000ffd1-0000-1000-8000-00805f9b34fb"   # write
VD_N   = "0000ffd2-0000-1000-8000-00805f9b34fb"   # notify
VD_WN  = "0000ffd3-0000-1000-8000-00805f9b34fb"   # write + notify
KNOWN = {
    OTA_SVC: "OTA service (OTA mode only)", OTA_RX: "OTA RX", OTA_TX: "OTA TX",
    VENDOR_SVC: "Vendor 128 (OTA mode only)", VENDOR_RX: "Vendor RX", VENDOR_TX: "Vendor TX",
    PF_SVC: "protocol_file_tran svc (DFU)", PF_RX: "file_tran RX (write)", PF_TX: "file_tran TX (notify)",
    VD_SVC: "vendor ffd0 svc", VD_W: "ffd1 write", VD_N: "ffd2 notify", VD_WN: "ffd3 write+notify",
}
# notification characteristics to observe in normal mode
OBSERVE_TX = [PF_TX, VD_N, VD_WN, OTA_TX, VENDOR_TX]


async def do_scan(timeout):
    print(f"scanning for {timeout}s ...")
    devs = await BleakScanner.discover(timeout=timeout)
    for d in sorted(devs, key=lambda x: (x.name or "")):
        print(f"  {d.address}   rssi={getattr(d,'rssi','?'):>4}   {d.name or '(unnamed)'}")
    print(f"total: {len(devs)}")


async def resolve(name, addr, timeout):
    if addr:
        return addr
    devs = await BleakScanner.discover(timeout=timeout)
    for d in devs:
        if name and d.name and name.lower() in d.name.lower():
            print(f"found: {d.name} [{d.address}]")
            return d.address
    sys.exit(f"no device found with name ~ '{name}'")


def notify_cb(sender, data: bytearray):
    print(f"  [NOTIFY] {sender}: len={len(data)}  {data.hex(' ')}")


async def dump(name, addr, observe, timeout):
    address = await resolve(name, addr, timeout)
    print(f"connecting to {address} ...")
    async with BleakClient(address) as client:
        print(f"connected: {client.is_connected}")
        try:
            print(f"MTU: {client.mtu_size}")
        except Exception:
            pass

        present = set()
        print("\n=== GATT TABLE ===")
        for svc in client.services:
            tag = KNOWN.get(svc.uuid.lower(), "")
            print(f"[SERVICE] {svc.uuid}  {('<'+tag+'>') if tag else ''}")
            present.add(svc.uuid.lower())
            for ch in svc.characteristics:
                ctag = KNOWN.get(ch.uuid.lower(), "")
                props = ",".join(ch.properties)
                print(f"    [CHAR] {ch.uuid}  handle=0x{ch.handle:04x}  props=[{props}]  "
                      f"{('<'+ctag+'>') if ctag else ''}")
                present.add(ch.uuid.lower())
                for de in ch.descriptors:
                    print(f"        [DESC] {de.uuid}  handle=0x{de.handle:04x}")

        print("\n=== known service presence ===")
        for u, label in KNOWN.items():
            print(f"  {'OK ' if u in present else '-- '} {label:20s} {u}")

        # Observe notifications (subscriptions configure CCCD, not application data)
        subs = [u for u in OBSERVE_TX if u in present]
        if observe > 0 and subs:
            print(f"\n=== observing notifications for {observe}s (no application data writes) ===")
            for u in subs:
                try:
                    await client.start_notify(u, notify_cb)
                    print(f"  subscribed to {u}")
                except Exception as e:
                    print(f"  could not subscribe to {u}: {e}")
            await asyncio.sleep(observe)
            for u in subs:
                try:
                    await client.stop_notify(u)
                except Exception:
                    pass
        print("\nreconnaissance complete (no application data written).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scan", action="store_true", help="list devices only")
    p.add_argument("--name", help="connect to the first device whose name contains this text")
    p.add_argument("--addr", help="connect using an exact MAC address/UUID")
    p.add_argument("--observe", type=int, default=20, help="seconds to observe notifications")
    p.add_argument("--timeout", type=float, default=10.0, help="scan timeout")
    a = p.parse_args()
    if a.scan or (not a.name and not a.addr):
        asyncio.run(do_scan(a.timeout))
    else:
        asyncio.run(dump(a.name, a.addr, a.observe, a.timeout))


if __name__ == "__main__":
    main()
