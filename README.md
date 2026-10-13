# Cubitt VIVA Pro 2 - Reverse Engineering

Documentation and tools from the reverse engineering of the **Cubitt VIVA Pro 2** firmware and Bluetooth protocol. The goal is to understand how the app communicates with the watch, how updates are packaged, and what remains to be done to develop reproducible modifications. An independent project, unaffiliated with Cubitt, Creek, or Actions Technology.

**Downloads:** no modified firmware is currently available to install. The guide explains how to extract and study the original image from your own APK. The local Gemini/DeepSeek changes concern the Android app and its proxy; they do not modify the watch firmware.

## What you can do with this repository

| Activity | Getting started | Result |
|---|---|---|
| Obtain the original reference image | [Extraction guide](docs/FIRMWARE_RESEARCH.md) and your own APK | A `zephyr.fw` container and payload for local analysis |
| Check integrity and identify the sample | `repack_ota.py verify` and SHA256 | Comparison with the documented CRC32, lengths, and hashes |
| Study the firmware code | Ghidra and `analysis/ghidra_scripts/` | Functions, references, and call paths for the analyzed sample |
| Explore the watch's Bluetooth services | `cubitt_ble_recon.py` and the [BLE checklist](docs/BLE_CHECKLIST.md) | Service and characteristic inventory, with optional notification observation |
| Understand app communication | [BLE protocol notes](docs/BLE_WIRE_PROTOCOL.md) | Documented interpretation of C1 frames and D1-D4 transfers |
| Experiment with the container without connecting to the watch | `repack_ota.py extract`, `build`, and `patch` | Locally repacked files with the container CRC32 recalculated |
| Continue the research | Compare another version and document differences | New evidence about formats, platform, and transport |

Repacking produces an experimental file. The published tools do not implement a modified firmware installer or a ready-to-use Gemini/DeepSeek integration.

## Research process

1. **Android app inspection.** The package and libraries were inventoried, strings related to OTA, BLE, and voice were searched, and APK assets were inspected.
2. **Container extraction and analysis.** `zephyr.fw` was found in the assets, and its bytes, sizes, and CRC were checked. The initial assumption that the payload started at `0x240` was corrected to `0x40`.
3. **Static analysis in Ghidra.** Transfer, validation, and SDFS item functions were studied through decompilation and cross-references. The included scripts help repeat that exploration on the same sample.
4. **Platform SDK comparison.** Names, structures, and paths were matched against the public Actions SDK. These correspondences guide the research; they do not independently confirm the watch's configuration.
5. **BLE observation.** The notes record GATT exploration and instrumented captures of app-watch communication. C1 frames, raw D1-D4 transport, and SDFS items were distinguished. The original instrumentation scripts and complete captures are not included; the technical observations and GATT explorer are published.

This process produced corrections and open questions. When interpreting the findings, distinguish bytes verified in the sample, observations recorded on the watch, and hypotheses derived from the SDK.

## Status

- A `zephyr.fw` image bundled with the Cubitt Pro 2.1.11 APK was analyzed. Its presence in the APK does not prove that it is installed on, or compatible with, every unit.
- The analyzed container has a `0x40`-byte header, a 1,252,000-byte payload, and CRC32 `0x673bafc8`.
- The notes identify evidence of Zephyr and the Actions ATS3085 family. The exact hardware variant and the watch's partition map require independent confirmation.
- GATT services and captures of the C1 and file_tran D1-D4 protocols were documented.
- There is no buildable custom firmware or validated flashing and recovery procedure. Bootloader acceptance of modified images remains unverified.

The July 2026 notes preserve findings and hypotheses from different stages. Historical claims of "no signature," "confirmed recovery," or "zero risk" are not hardware validation. Later corrections within each document take precedence over initial observations.

## Contents

| Path | Contents |
|---|---|
| [docs/FIRMWARE_RESEARCH.md](docs/FIRMWARE_RESEARCH.md) | Local image acquisition and reproducible verification |
| [docs/PLATFORM_SDK.md](docs/PLATFORM_SDK.md) | Proposed correspondences with the Actions SDK |
| [docs/DFU_PROTOCOL.md](docs/DFU_PROTOCOL.md) | Container, image, and SDFS item formats |
| [docs/BLE_WIRE_PROTOCOL.md](docs/BLE_WIRE_PROTOCOL.md) | BLE captures and protocol interpretation |
| [docs/BLE_OTA_ROUTE.md](docs/BLE_OTA_ROUTE.md) | Historical OTA path research |
| [docs/BLE_CHECKLIST.md](docs/BLE_CHECKLIST.md) | Manual BLE service recording |
| [docs/APK_ANALYSIS.md](docs/APK_ANALYSIS.md) | Local APK inspection |
| [analysis/reports/phase1_signature_verdict.md](analysis/reports/phase1_signature_verdict.md) | Historical evidence about integrity and signatures |
| `tools/repack/` | Verification, extraction, repacking, and experimental checksums |
| `tools/ble/` | GATT scanning and notification observation with Bleak |
| `tools/*.ps1` | ADB inventory, APK extraction, and firmware/log searches |
| `analysis/ghidra_scripts/` | Ghidra scripts with addresses specific to the analyzed image |

## Local usage

```powershell
git clone https://github.com/Dasannn/cubitt-firmware.git
cd cubitt-firmware
```

Use Python 3 for repacking, and PowerShell plus Android SDK Platform Tools for the ADB scripts. The latter look for `adb.exe` in `%LOCALAPPDATA%\Android\Sdk\platform-tools`. Run commands from the repository root.

```powershell
py tools/repack/crc_filetran.py
py tools/repack/repack_ota.py verify analysis/firmware_candidates/zephyr.fw
py tools/repack/repack_ota.py extract analysis/firmware_candidates/zephyr.fw analysis/firmware_candidates/zephyr_image.bin
```

First obtain your `.fw` file using the [extraction guide](docs/FIRMWARE_RESEARCH.md). The repacker's `build` and `patch` commands produce local files; recalculating the container CRC does not validate the contents or guarantee that they will boot. Always use an output path different from the original.

To explore BLE, install the optional dependency and scan:

```powershell
py -m pip install bleak
py tools/ble/cubitt_ble_recon.py --scan
py tools/ble/cubitt_ble_recon.py --addr AA:BB:CC:DD:EE:FF --observe 0
```

Replace the example address with your watch's address. `--observe 0` disables subscriptions; the default is 20 seconds. Subscribing to notifications configures the CCCD even though it sends no application data or update commands.

The Ghidra scripts use base address `0x10010000` and addresses from the image identified in the guide. Their results do not automatically apply to other versions.

## Contributing

Open an issue or pull request with corrections, differences between versions, or reproducible results. Include the model, app version, image SHA256, tool used, and steps to repeat the observation. Distinguish the observed result from its interpretation.

Next steps include confirming the hardware variant, checking the checksums against more samples, studying the actual bootloader, and validating backup and recovery before testing modified firmware. Share only minimal anonymized evidence; remove device addresses, contacts, tokens, and other personal data.

## Excluded files

APKs, firmware images, third-party SDKs, Ghidra installations, captures, databases, keys, certificates, logs, personal data, and generated files are not distributed. The Gemini Bridge app and AI proxies are also outside the firmware scope. Historical references to `scratchpad/` point to scripts unavailable in this publication.

The `.gitignore` allows only reviewed files by exact name. Review any new document before allowing it: a report may contain identifiers or credentials even when it is plain text. This exclusion does not protect against secrets added to an already tracked file or against `git add -f`.

## License

The original code and documentation in this repository are released under the [MIT License](LICENSE). You may use, modify, and redistribute them, including commercially, provided you retain the copyright and license notice. Contributions are welcome under the same license.

This license does not grant rights to third-party firmware, APKs, SDKs, or quoted third-party material. Those remain subject to their respective terms.

## References

- Reference SDK: https://github.com/lvgl/lv_port_actions_technology
- Research on another Actions platform: https://github.com/ovsky/RE-ATS3603

External resources retain their own terms. This repository does not relicense them or redistribute their complete contents.

## Publication validation

The SHA256 hashes, sizes, and CRC32 of the local reference files were verified, and `crc_filetran.py` was run with its existing vectors. This checks local consistency, not equivalence of every checksum with the device. No flashing, BLE/ADB tests, or Ghidra scripts were run during publication preparation.
