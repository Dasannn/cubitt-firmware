# Safe analysis of the Cubitt Pro APK

Goal: look for VITA AI, BLE, firmware, or OTA clues without modifying anything.

## Tools

- Android Studio, optional.
- `jadx-gui`, to read Java/Kotlin code from the APK.
- `tools/scan_cubitt_apk.ps1`, for an initial local string scan.

## Obtain the APK

Use a legitimate copy of the `Cubitt Pro` app installed on your phone or downloaded from a source you are entitled to use.

Expected app:

```text
Name: Cubitt Pro
Package: com.cubittpros.wear
```

If your phone is connected through ADB:

```powershell
.\tools\pull_cubitt_apk.ps1
```

## Quick PowerShell scan

Place the APK in a local directory, for example:

```text
apks/cubitt-pro.apk
```

Run from the project root:

```powershell
.\tools\scan_cubitt_apk.ps1 -ApkPath .\apks\cubitt-pro.apk
```

The script generates a report in:

```text
analysis/
```

Look especially for:

- `https://...` URLs
- `vita`
- `voice`
- `speech`
- `ota`
- `dfu`
- `firmware`
- `upgrade`
- `gatt`
- `uuid`
- `bluetooth`
- SDK or manufacturer names

## Analysis with jadx-gui

1. Open `jadx-gui`.
2. Load the APK.
3. Use global search.
4. Search for the same keywords.
5. If you find OTA, BLE, or VITA classes, record:
   - Class name.
   - Package.
   - UUIDs.
   - URLs.
   - `.bin`, `.fw`, `.zip`, or `.json` filenames.

## What we are looking for

The key question is:

```text
When you speak to VITA AI on the watch, does the audio/command pass through Cubitt Pro?
```

If so, replacing that path with Gemini could be investigated without changing firmware.

If not, and VITA runs inside the firmware or on closed servers, an actual replacement would depend on firmware work.

## Next firmware step

Follow `docs/FIRMWARE_RESEARCH.md` to capture logs, search for cached firmware, and identify the OTA mechanism before attempting any modification.
