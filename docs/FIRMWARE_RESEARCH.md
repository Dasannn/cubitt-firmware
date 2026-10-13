# Local firmware acquisition and analysis

## 1. Obtain the APK

With your own phone connected and authorized through ADB:

```powershell
.\tools\pull_cubitt_apk.ps1
```

Output is saved in `apks/com.cubittpros.wear-<timestamp>/`. You can also use a legitimate copy of your APK. This publication does not include the app or its binaries.

## 2. Extract the asset

The analyzed APK contained this internal ZIP entry:

```text
assets/flutter_assets/packages/creek_blue_manage/assets/images/zephyr.fw
```

Open `base.apk` as a ZIP archive and copy only that asset to `analysis/firmware_candidates/zephyr.fw`, creating the directory first. It may be absent or different in other versions. Do not execute extracted files.

## 3. Verify and extract the payload

```powershell
py tools/repack/repack_ota.py verify analysis/firmware_candidates/zephyr.fw
py tools/repack/repack_ota.py extract analysis/firmware_candidates/zephyr.fw analysis/firmware_candidates/zephyr_image.bin
Get-FileHash analysis/firmware_candidates/zephyr.fw -Algorithm SHA256
Get-FileHash analysis/firmware_candidates/zephyr_image.bin -Algorithm SHA256
```

Proceed with extraction only if `verify` succeeds.

| Reference file | Bytes | SHA256 |
|---|---:|---|
| `zephyr.fw` | 1252064 | `8d08723ed8dd12ab659a58edbd8a64ede3c416716f6ae49ccee9400714ebfd6a` |
| `zephyr_image.bin` | 1252000 | `f27f23ad76b697ecdc5f9563fdb7016574a6b2fc283da664685732c6cd781606` |

The payload starts at `0x40`, not `0x240`. The field at `0x0C` is the payload CRC32, not a date. The sample CRC32 is `0x673bafc8`. These values correct the initial extraction report, omitted from this publication because it was outdated.

## 4. Investigate

- Import the payload as a little-endian ARM binary in Ghidra at base address `0x10010000`; check Thumb mode and the vector table.
- Add `analysis/ghidra_scripts/` to the Script Manager to explore the documented functions. Addresses are fixed for the sample above.
- Read [DFU_PROTOCOL.md](DFU_PROTOCOL.md) for format analysis and [BLE_WIRE_PROTOCOL.md](BLE_WIRE_PROTOCOL.md) for transport observations.
- Use `tools/adb_cubitt_inventory.ps1`, `tools/find_cubitt_firmware_files.ps1`, and `tools/capture_cubitt_logcat.ps1` to generate additional local evidence. The capture script clears the logcat buffer at startup; reports may contain personal data and remain excluded from Git.

## Pending work

Confirm the exact hardware, obtain a complete backup, and verify the bootloader and recovery method before attempting to install modified images. A match with a reference SDK or a correct CRC does not replace these checks.
