# BLE checklist for Cubitt VIVA Pro 2

Goal: observe Bluetooth without writing data or modifying the watch.

## Tool

Install on Android:

```text
nRF Connect for Mobile
```

## Rules

- Do not write values to BLE characteristics.
- Do not run DFU/OTA commands.
- Only scan, connect if necessary, and take screenshots.
- If you see a `Write`, `Upload`, `DFU`, or `Update` option, do not use it yet.

## Scan 1: watch without Cubitt Pro open

1. Close Cubitt Pro.
2. Open `nRF Connect`.
3. Tap `Scan`.
4. Look for names such as `Cubitt`, `VIVA`, `VIVA PRO`, or a device with a strong signal.
5. Save screenshots of:
   - Advertised name.
   - BLE address or identifier.
   - RSSI.
   - Advertising data.

## Scan 2: watch paired normally

1. Open Cubitt Pro and connect the watch.
2. Return to `nRF Connect`.
3. Repeat the scan.
4. Compare whether the name, services, or state changed.

## If you can connect from nRF Connect

Document:

- GATT services.
- UUIDs.
- `Read`, `Notify`, `Indicate`, and `Write` characteristics.
- Any text related to:
  - `OTA`
  - `DFU`
  - `Firmware`
  - `Voice`
  - `AI`
  - `Audio`

## Results template

Copy this into your notes:

```text
Visible model:
BLE name:
BLE address/ID:
Date:
Android phone:
Cubitt Pro open: yes/no

Services:
- UUID:
  - Characteristics:
  - Permissions:
  - Notes:

OTA/DFU observed: yes/no
Voice/audio/AI observed: yes/no
Screenshots saved: yes/no
```

## Interpretation

- Voice/audio services may indicate a flow through the phone.
- If only health/notification services are present, VITA AI is probably more closed.
- OTA/DFU support does not yet mean that firmware can be modified; format, signature, chip, and recovery information are still needed.
