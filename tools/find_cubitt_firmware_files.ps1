param(
    [string]$OutDir = "analysis"
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) {
    throw "adb not found at $adb"
}

$devices = & $adb devices
$deviceRows = $devices | Select-Object -Skip 1 | Where-Object { $_ -match "\bdevice$" }
if (-not $deviceRows) {
    throw "No Android phones connected through ADB. Connect the phone, authorize USB debugging, and run again."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outRoot = Join-Path (Get-Location) $OutDir
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$reportPath = Join-Path $outRoot "cubitt-firmware-file-search-$timestamp.txt"

$commands = @(
    "find /sdcard/Download -maxdepth 3 -type f 2>/dev/null",
    "find /sdcard/Documents -maxdepth 3 -type f 2>/dev/null",
    "find /sdcard/Android/data/com.cubittpros.wear -maxdepth 6 -type f 2>/dev/null",
    "find /sdcard/Android/media/com.cubittpros.wear -maxdepth 6 -type f 2>/dev/null"
)

$patterns = "cubitt|viva|watch|ota|dfu|firmware|upgrade|\.bin$|\.fw$|\.zip$|\.img$|\.dat$|\.json$"

$report = New-Object System.Collections.Generic.List[string]
$report.Add("Cubitt firmware file search")
$report.Add("Generated: $(Get-Date -Format s)")
$report.Add("")

foreach ($command in $commands) {
    $report.Add("== adb shell $command ==")
    $lines = & $adb shell $command
    $matched = $lines | Select-String -Pattern $patterns | ForEach-Object { $_.Line }
    if ($matched) {
        foreach ($line in $matched) {
            $report.Add($line)
        }
    } else {
        $report.Add("(no interesting files found)")
    }
    $report.Add("")
}

$report | Set-Content -Path $reportPath -Encoding UTF8
Write-Host "Report written to $reportPath"
